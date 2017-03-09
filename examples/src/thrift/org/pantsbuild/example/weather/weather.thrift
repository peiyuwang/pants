// Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

namespace java org.pantsbuild.example.weather.thriftjava
#@namespace scala org.pantsbuild.example.weather.thriftscala
namespace py org.pantsbuild.example.weather

include "org/pantsbuild/example/precipitation/precipitation.thrift"

struct Weather {
  1: optional string date;
  2: optional precipitation.Precipitation precipitation;
}
