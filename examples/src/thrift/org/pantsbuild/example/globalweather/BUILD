java_thrift_library(name='globalweather-java',
  sources=['globalweather.thrift'],
  dependencies=[
    'examples/src/thrift/org/pantsbuild/example/weather:weather-java',
  ],
)

java_thrift_library(name='globalweather-scala',
  sources=['globalweather.thrift'],
  compiler='scrooge',
  language='scala',
  rpc_style='finagle',
  dependencies=[
   # This is necessary to compile
   'examples/src/thrift/org/pantsbuild/example/distance:distance-scala',
   'examples/src/thrift/org/pantsbuild/example/precipitation:precipitation-scala',
   'examples/src/thrift/org/pantsbuild/example/weather:weather-scala',
  ],
)
