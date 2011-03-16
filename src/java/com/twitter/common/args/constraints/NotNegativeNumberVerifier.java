// =================================================================================================
// Copyright 2011 Twitter, Inc.
// -------------------------------------------------------------------------------------------------
// Licensed to the Apache Software Foundation (ASF) under one or more contributor license
// agreements.  See the NOTICE file distributed with this work for additional information regarding
// copyright ownership.  The ASF licenses this file to you under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with the License.  You may
// obtain a copy of the License at
//
//  http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the
// License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
// express or implied.  See the License for the specific language governing permissions and
// limitations under the License.
// =================================================================================================

package com.twitter.common.args.constraints;

import static com.google.common.base.Preconditions.checkArgument;

/**
 * Verifier to ensure that a number is non-negative.
 *
 * @author William Farner
 */
public class NotNegativeNumberVerifier extends ScalarVerifier<Number> {
  @Override
  public void verify(Number number) {
    checkArgument(number.doubleValue() >= 0, "Value must be non-negative.");
  }
}
