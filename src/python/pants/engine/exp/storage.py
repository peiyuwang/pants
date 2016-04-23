# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import cPickle as pickle
import logging
import StringIO
import sys
from abc import abstractmethod
from binascii import hexlify
from collections import Counter
from contextlib import closing
from functools import total_ordering
from hashlib import sha1
from struct import Struct as StdlibStruct

import lmdb
import six

from pants.engine.exp.objects import Closable, SerializationError
from pants.engine.exp.scheduler import StepRequest, StepResult
from pants.util.dirutil import safe_mkdtemp
from pants.util.meta import AbstractClass


logger = logging.getLogger(__name__)


@total_ordering
class Key(object):
  """Holds the digest for the object, which uniquely identifies it.

  The `_hash` is a memoized 32 bit integer hashcode computed from the digest.

  The `string` field holds the string representation of the object, but is optional (usually only
  used when debugging is enabled).

  NB: Because `string` is not included in equality comparisons, we cannot just use `datatype` here.
  """

  __slots__ = ['_digest', '_type', '_hash', '_string']

  # The digest implementation used for Keys.
  _DIGEST_IMPL = sha1
  _DIGEST_SIZE = _DIGEST_IMPL().digest_size

  # A struct.Struct definition for grabbing the first 4 bytes off of a digest of
  # size DIGEST_SIZE, and discarding the rest.
  _32_BIT_STRUCT = StdlibStruct(b'<l' + (b'x' * (_DIGEST_SIZE - 4)))

  @classmethod
  def create(cls, blob, type_, string=None):
    """Given a blob, hash it to construct a Key.

    :param blob: Binary content to hash.
    :param type_: Type of the object to be hashed.
    :param string: An optional human-readable representation of the blob for debugging purposes.
    """
    digest = cls._DIGEST_IMPL(blob).digest()
    hash_ = cls.compute_hash_from_digest(digest)
    return cls(digest, hash_, type_, string)

  @classmethod
  def compute_hash_from_digest(cls, digest):
    """Extract 32 bit hash from digest."""
    return cls._32_BIT_STRUCT.unpack(digest)[0]

  def __init__(self, digest, hash_, type_, string):
    """Not for direct use: construct a Key via `create` instead."""
    self._digest = digest
    self._hash = hash_
    self._type = type_
    self._string = string

  @property
  def string(self):
    return self._string

  @property
  def digest(self):
    return self._digest

  @property
  def type(self):
    return self._type

  def __hash__(self):
    return self._hash

  def __eq__(self, other):
    return type(other) == Key and self._digest == other._digest

  def __lt__(self, other):
    return self._digest < other._digest

  def __repr__(self):
    return 'Key({}{})'.format(
        hexlify(self._digest),
        '' if self._string is None else ':[{}]'.format(self._string))

  def __str__(self):
    return repr(self)


class InvalidKeyError(Exception):
  """Indicate an invalid `Key` entry"""


class Storage(Closable):
  """Stores and creates unique keys for input Serializable objects.

  Storage as `Closable`, `close()` can be called either explicitly or through the `with`
  statement in a context.

  Besides contents indexed by their hashed Keys, a secondary index is also provided
  for mappings between Keys. This allows to establish links between contents that
  are represented by those keys. Cache for example is such a use case.

  Convenience methods to translate nodes and states in
  `pants.engine.exp.scheduler.StepRequest` and `pants.engine.exp.scheduler.StepResult`
  into keys, and vice versa are also provided.
  """

  LMDB_KEY_MAPPINGS_DB_NAME = b'_key_mappings_'

  @classmethod
  def create(cls, path=None, in_memory=False, debug=True, protocol=None):
    """Create a content addressable Storage backed by a key value store.

    :param path: If in_memory=False, the path to store the database in.
    :param in_memory: Indicate whether to use the in-memory kvs or an embeded database.
    :param debug: A flag to store debug information in the key.
    :param protocol: Serialization protocol for pickle, if not provided will use ASCII protocol.
    """
    if in_memory:
      content, key_mappings = InMemoryDb(), InMemoryDb()
    else:
      content, key_mappings = Lmdb.create(path=path,
                                          child_databases=[cls.LMDB_KEY_MAPPINGS_DB_NAME])

    return Storage(content, key_mappings, debug=debug, protocol=protocol)

  @classmethod
  def clone(cls, storage):
    """Clone a Storage so it can be shared across process boundary."""
    if isinstance(storage._contents, InMemoryDb):
      contents, key_mappings = storage._contents, storage._key_mappings
    else:
      contents, key_mappings = Lmdb.create(path=storage._contents.path,
                                           child_databases=[cls.LMDB_KEY_MAPPINGS_DB_NAME])

    return Storage(contents, key_mappings, debug=storage._debug, protocol=storage._protocol)

  def __init__(self, contents, key_mappings, debug=True, protocol=None):
    """Not for direct use: construct a Storage via either `create` or `clone`."""
    self._contents = contents
    self._key_mappings = key_mappings
    self._debug = debug
    self._protocol = protocol if protocol is not None else pickle.HIGHEST_PROTOCOL

  def put(self, obj):
    """Serialize and hash a Serializable, returning a unique key to retrieve it later.

    NB: pickle by default memoizes objects by id and pickle repeated objects by references,
    for example, (A, A) uses less space than (A, A'), A and A' are equal but not identical.
    For content addressability we need equality. Use `fast` mode to turn off memo.
    Longer term see https://github.com/pantsbuild/pants/issues/2969
    """
    try:
      with closing(StringIO.StringIO()) as buf:
        pickler = pickle.Pickler(buf, protocol=self._protocol)
        pickler.fast = 1
        pickler.dump(obj)
        blob = buf.getvalue()
    except Exception as e:
      # Unfortunately, pickle can raise things other than PickleError instances.  For example it
      # will raise ValueError when handed a lambda; so we handle the otherwise overly-broad
      # `Exception` type here.
      raise SerializationError('Failed to pickle {}: {}'.format(obj, e))

    # Hash the blob and store it if it does not exist.
    key = Key.create(blob, type(obj), str(obj) if self._debug else None)

    self._contents.put(key.digest, blob)

    # have to sample travis only allow 4Mb log file
    #if '[(SelectNode' in str(key) or 'Noop' in str(key):
    #  sys.stderr.write('Under: {}\n'.format(key))
    assert self.get(key) == obj
    return key

  def puts(self, objs):
    """Save objects to storage in bulk.

    Keys are returned as a list, ordering is preserved.
    """
    keys = []
    for obj in objs:
      keys.append(self.put(obj))
    return keys

  def get(self, key):
    """Given a key, return its deserialized content.

    Note that since this is not a cache, if we do not have the content for the object, this
    operation fails noisily.
    """
    if not isinstance(key, Key):
      raise InvalidKeyError('Not a valid key: {}'.format(key))

    value = self._contents.get(key.digest)

    try:
      if isinstance(value, six.binary_type):
        # loads for string-like values
        unpickled_data = pickle.loads(value)
      else:
        # load for file-like value from buffers
        unpickled_data = pickle.load(value)
      return self._assert_type_matches(unpickled_data, key.type)
    except (pickle.UnpicklingError, EOFError, ValueError):
      if isinstance(value, six.binary_type):
        sys.stderr.write('key={}/{}\n{}\n'.format(key, key.type, hexlify(value)))
      else:
        sys.stderr.write('key={}/{}\n{}\n'.format(key, key.type, hexlify(value.getvalue())))
      raise

  def add_mapping(self, from_key, to_key):
    """Establish one to one relationship from one Key to another Key.

    Content that keys represent should either already exist or the caller must
    check for existence.

    Unlike content storage, key mappings allows overwriting existing entries,
    meaning a key can be re-mapped to a different key.
    """
    self._key_mappings.put(key=from_key.digest,
                           value=pickle.dumps(to_key, protocol=self._protocol))
    assert to_key == self.get_mapping(from_key)

  def get_mapping(self, from_key):
    """Retrieve the mapping Key from a given Key.

    None is returned if the mapping does not exist.
    """
    to_key = self._key_mappings.get(key=from_key.digest)

    if to_key is None:
      return None

    try:
      if isinstance(to_key, six.binary_type):
        # loads for string-like values
        unpickled_data = pickle.loads(to_key)
      else:
        # load for file-like value from buffers
        unpickled_data = pickle.load(to_key)
      return unpickled_data
    except (pickle.UnpicklingError, EOFError, ValueError):
      if isinstance(to_key, six.binary_type):
        sys.stderr.write('get_mapping from_key={} to_key={}\n{}\n'.format(from_key, to_key, hexlify(to_key)))
      else:
        sys.stderr.write('get_mapping from_key={} to_key={}\n{}\n'.format(from_key, to_key, hexlify(to_key.getvalue())))
      raise

  def close(self):
    self._contents.close()

  def _assert_type_matches(self, value, key_type):
    """Ensure the type of deserialized object matches the type from key."""
    value_type = type(value)
    if key_type and value_type is not key_type:
      raise ValueError('Mismatch types, key: {}, value: {}'
                       .format(key_type, value_type))
    return value

  def key_for_request(self, step_request):
    """Make keys for the dependency nodes as well as their states in step_request.

    step_request.node isn't keyed is only for convenience because it is used
    in a subsequent is_cacheable check.
    """
    dependencies = {}
    for dep, state in step_request.dependencies.items():
      dependencies[self._to_key(dep)] = self._to_key(state)
    return StepRequest(step_request.step_id, step_request.node,
                       dependencies, step_request.project_tree)

  def key_for_result(self, step_result):
    """Make key for result state."""
    return StepResult(state=self._to_key(step_result.state))

  def resolve_request(self, step_request):
    """Resolve keys in step_request."""
    dependencies = {}
    for dep, state in step_request.dependencies.items():
      dependencies[self._from_key(dep)] = self._from_key(state)

    return StepRequest(step_request.step_id, step_request.node,
                       dependencies, step_request.project_tree)

  def resolve_result(self, step_result):
    """Resolve state key in step_result."""
    return StepResult(state=self._from_key(step_result.state))

  def _to_key(self, obj):
    if isinstance(obj, Key):
      return obj
    return self.put(obj)

  def _from_key(self, obj):
    if isinstance(obj, Key):
      return self.get(obj)
    return obj


class Cache(Closable):
  """Cache StepResult for a given StepRequest.

  NB: since Subjects in Nodes can be anything, comparison among them are usually N/A,
  both cache get and put are for a keyed `StepRequest`.
  """

  @classmethod
  def create(cls, storage=None, cache_stats=None):
    """Create a Cache from a given storage instance."""

    storage = storage or Storage.create()
    cache_stats = cache_stats or CacheStats()
    return Cache(storage, cache_stats)

  def __init__(self, storage, cache_stats):
    """Initialize the cache. Not for direct use, use factory methods `create`.

    :param storage: Main storage for all requests and results.
    :param cache_stats: Stats for hits and misses.
    """
    self._storage = storage
    self._cache_stats = cache_stats

  def get(self, step_request):
    """Get the cached StepResult for a given StepRequest."""
    result_key = self._storage.get_mapping(self._storage.put(self._keyable_fields(step_request)))
    if result_key is None:
      self._cache_stats.add_miss()
      return None

    self._cache_stats.add_hit()
    return self._storage.get(result_key)

  def put(self, step_request, step_result):
    """Save the StepResult for a given StepResult."""
    request_key = self._storage.put(self._keyable_fields(step_request))
    result_key = self._storage.put(step_result)
    return self._storage.add_mapping(from_key=request_key, to_key=result_key)

  def get_stats(self):
    return self._cache_stats

  def items(self):
    """Iterate over all cached request, result for testing purpose."""
    for digest, _ in self._storage._key_mappings.items():
      # Construct request key from digest directly because we do not have the
      # request blob.  Type check is intentionally skipped because we do not
      # want to introduce a dependency from `storage` to `scheduler`
      request_key = Key(digest=digest, hash_=Key.compute_hash_from_digest(digest),
                        type_=None, string=None)
      request = self._storage.get(request_key)
      yield request, self._storage.get(self._storage.get_mapping(self._storage.put(request)))

  def _keyable_fields(self, step_request):
    """Return fields for the purpose of computing the cache key of this step request.

    Some special handling is needed to compute cache key for step request.
    First step_id should be dropped, because it's only an identifier not part
    of the input for execution. We also want to sort the dependencies map by
    keys, i.e, node_keys, to eliminate non-determinism.
    """
    sorted_deps = sorted(step_request.dependencies.items(), key=lambda t: (type(t[0]), t[0]))
    return (step_request.node, sorted_deps, step_request.project_tree)

  def close(self):
    self._storage.close()


class CacheStats(Counter):
  """Record cache hits and misses."""

  HIT_KEY = 'hits'
  MISS_KEY = 'misses'

  def add_hit(self):
    """Increment hit count by 1."""
    self[self.HIT_KEY] += 1

  def add_miss(self):
    """Increment miss count by 1."""
    self[self.MISS_KEY] += 1

  @property
  def hits(self):
    """Raw count for hits."""
    return self[self.HIT_KEY]

  @property
  def misses(self):
    """Raw count for misses."""
    return self[self.MISS_KEY]

  @property
  def total(self):
    """Total count including hits and misses."""
    return self[self.HIT_KEY] + self[self.MISS_KEY]

  def __repr__(self):
    return 'hits={}, misses={}, total={}'.format(self.hits, self.misses, self.total)


class KeyValueStore(Closable, AbstractClass):
  @abstractmethod
  def get(self, key):
    """Fetch the value for a given key.

    :param key: key in bytestring.
    :return: value can be either string-like or file-like, `None` if does not exist.
    """

  @abstractmethod
  def put(self, key, value):
    """Save the value under a key, but only once.

    The write once semantics is specifically provided for the content addressable use case.

    :param key: key in bytestring.
    :param value: value in bytestring.
    :return: `True` to indicate the write actually happens, i.e, first write, `False` for
      repeated writes of the same key.
    """

  @abstractmethod
  def items(self):
    """Generator to iterate over items.

    For testing purpose.
    """


class InMemoryDb(KeyValueStore):
  """An in-memory implementation of the kvs interface."""

  def __init__(self):
    self._storage = dict()

  def get(self, key):
    return self._storage.get(key)

  def put(self, key, value):
    if key in self._storage:
      return False
    self._storage[key] = value
    return True

  def items(self):
    for k in iter(self._storage):
      yield k, self._storage.get(k)


class Lmdb(KeyValueStore):
  """A lmdb implementation of the kvs interface."""

  # TODO make this more configurable through a subsystem.

  # 256GB - some arbitrary maximum size database may grow to.
  MAX_DATABASE_SIZE = 256 * 1024 * 1024 * 1024

  # writemap will use a writeable memory mapping to directly update storage, therefore
  # improves performance. But it may cause filesystems that don’t support sparse files,
  # such as OSX, to immediately preallocate map_size = bytes of underlying storage.
  # See https://lmdb.readthedocs.org/en/release/#writemap-mode
  USE_SPARSE_FILES = sys.platform != 'darwin'

  @classmethod
  def create(self, path=None, child_databases=None):
    """
    :param path: Database directory location, if `None` a temporary location will be provided
      and cleaned up upon process exit.
    :param child_databases: Optional child database names.
    :return: List of Lmdb databases, main database under the path is always created,
     plus the child databases requested.
    """
    path = path if path is not None else safe_mkdtemp()
    child_databases = child_databases or []
    env = lmdb.open(path, map_size=self.MAX_DATABASE_SIZE,
                    metasync=False, sync=False, map_async=True,
                    writemap=self.USE_SPARSE_FILES,
                    max_dbs=1+len(child_databases))
    instances = [Lmdb(env)]
    for child_db in child_databases:
      instances.append(Lmdb(env, env.open_db(child_db)))
    return tuple(instances)

  def __init__(self, env, db=None):
    """Not for direct use, use factory method `create`.

    db if None represents the main database.
    """
    self._env = env
    self._db = db

  @property
  def path(self):
    return self._env.path()

  def get(self, key):
    """Return the value or `None` if the key does not exist.

    NB: Memory mapped storage returns a buffer object without copying keys or values, which
    is then wrapped with `StringIO` as the more friendly string buffer to allow `pickle.load`
    to read, again no copy involved.
    """
    with self._env.begin(db=self._db, buffers=True) as txn:
      value = txn.get(key)
      if value is not None:
        return StringIO.StringIO(value)
      return None

  def put(self, key, value):
    """Returning True if the key/value are actually written to the storage."""
    with self._env.begin(db=self._db, buffers=True, write=True) as txn:
      return txn.put(key, value, overwrite=False)

  def items(self):
    with self._env.begin(db=self._db, buffers=True) as txn:
      cursor = txn.cursor()
      for k, v in cursor:
        yield k, v

  def close(self):
    """Close the lmdb environment, calling multiple times has no effect."""
    self._env.close()
