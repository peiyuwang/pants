jar_library(
  name='zinc',
  jars=[
    scala_jar(org='org.scala-sbt', name='zinc', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              excludes=[
                exclude(org='org.scala-sbt', name='io_2.10'),
                exclude(org='org.scala-sbt', name='util-logging_2.10'),
              ],
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/zinc_2.10/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/zinc_2.10-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
    scala_jar(org='org.scala-sbt', name='zinc-core', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/zinc-core_2.10/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/zinc-core_2.10-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
    scala_jar(org='org.scala-sbt', name='compiler-interface', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/compiler-interface/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/compiler-interface-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
    scala_jar(org='org.scala-sbt', name='zinc-compile-core', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/zinc-compile-core_2.10/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/zinc-compile-core_2.10-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
    scala_jar(org='org.scala-sbt', name='zinc-persist', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/zinc-persist_2.10/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/zinc-persist_2.10-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
    scala_jar(org='org.scala-sbt', name='zinc-classpath', rev='1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd',
              url='file:///Users/peiyu/.m2/repository/org/scala-sbt/zinc-classpath_2.10/1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd/zinc-classpath_2.10-1.0.0-X2-SNAPSHOT-ed16a0eab94d0e5e5a8b202762f8dd54c4020dcd.jar',
              mutable=True),
  ],
)

jar_library(
  name='util-logging',
  jars=[
    # TODO: `zinc` only declares a dep on the `tests` classifier for
    # util-logging for some reason. We redefine the dep here to get the full package.
    scala_jar(org='org.scala-sbt', name='util-logging', rev='0.1.0-M13', force=True),
  ],
)

jar_library(
  name='io',
  jars=[
    # TODO: `zinc` only declares a dep on the `tests` classifier for
    # io. We redefine the dep here to get the full package.
    scala_jar(org='org.scala-sbt', name='io', rev='1.0.0-M6', force=True),
  ],
)
