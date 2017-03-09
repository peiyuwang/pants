// Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

package org.pantsbuild.example.hello.greet

object GreetScala {
}

trait G

trait GreetScala extends G
  with scala.Product2[String, Option[Long]]
  with java.io.Serializable
 {
}
