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

package com.twitter.common.thrift.text;

import java.util.Iterator;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;

/**
 * A parsing context used for Sequences (lists & sets). Maintains its
 * child elements, and a pointer to the current one being parsed.
 *
 * @author Alex Roetter
 */
class SequenceContext extends BaseContext {

  private final Iterator<JsonElement> children;
  private JsonElement currentChild;

  /**
   * Create an iterator over the children. May be constructed with a null
   * JsonArray if we only use it for writing.
   */
  protected SequenceContext(JsonArray json) {
    children = (null != json) ? json.iterator() : null;
  }

  @Override
  protected void read() {
    if (!children.hasNext()) {
      throw new RuntimeException(
          "Called SequenceContext.read() too many times!");
    }
    currentChild = children.next();
  }

  @Override
  protected JsonElement getCurrentChild() {
    return currentChild;
  }

  @Override
  protected boolean hasMoreChildren() {
    return children.hasNext();
  }
}
