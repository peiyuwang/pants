// Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

namespace java org.pantsbuild.example.globalweather.thriftjava
#@namespace scala org.pantsbuild.example.globalweather.thriftscala

namespace py org.pantsbuild.example.globalweather

include "org/pantsbuild/example/weather/weather.thrift"

struct GlobalWeather {
  1: optional string date;
  2: optional weather.Weather weather;
}
