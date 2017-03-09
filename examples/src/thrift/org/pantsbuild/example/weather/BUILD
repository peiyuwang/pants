java_thrift_library(name='weather-java',
  sources=['weather.thrift'],
  dependencies=[
    'examples/src/thrift/org/pantsbuild/example/precipitation:precipitation-java',
  ],
)

java_thrift_library(name='weather-scala',
  sources=['weather.thrift'],
  compiler='scrooge',
  language='scala',
  rpc_style='finagle',
  dependencies=[
   # This is necessary to compile
   'examples/src/thrift/org/pantsbuild/example/distance:distance-scala',
   'examples/src/thrift/org/pantsbuild/example/precipitation:precipitation-scala',
  ],
)
