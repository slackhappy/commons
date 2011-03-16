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

package com.twitter.common.net.loadbalancing;

import com.google.common.collect.Iterators;
import com.google.common.collect.Lists;
import com.twitter.common.net.pool.ResourceExhaustedException;

import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

/**
 * A load balancer that distributes load by randomizing the list of available backends, and then
 * rotating through them evenly.
 *
 * @author William Farner
 */
public class RoundRobinStrategy<S> extends StaticLoadBalancingStrategy<S> {

  private Iterator<S> iterator = Iterators.emptyIterator();

  @Override
  protected Collection<S> onBackendsOffered(Set<S> targets) {
    List<S> newTargets = Lists.newArrayList(targets);
    Collections.shuffle(newTargets);
    iterator = Iterators.cycle(newTargets);
    return newTargets;
  }

  @Override
  public S nextBackend() throws ResourceExhaustedException {
    if (!iterator.hasNext()) throw new ResourceExhaustedException("No backends available!");
    return iterator.next();
  }
}
