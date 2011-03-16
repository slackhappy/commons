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

package com.twitter.common.args.parsers;

import static com.google.common.base.Preconditions.checkArgument;

/**
 * Character parser.
 *
 * @author William Farner
 */
public class CharacterParser extends NonParameterizedTypeParser<Character> {

  public CharacterParser() {
    super(Character.class);
  }

  @Override
  public Character doParse(String raw) {
    checkArgument(raw.length() == 1,
        "String " + raw + " cannot be assigned to a character.");
    return raw.charAt(0);
  }
}
