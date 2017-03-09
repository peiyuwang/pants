// Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

package org.pantsbuild.example

object JvmRunExample {
}

trait J

trait JvmRunExample
  extends J
  with scala.Product2[String, Option[org.pantsbuild.example.hello.welcome.Welcome]]
  with java.io.Serializable
{
}
