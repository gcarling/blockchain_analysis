// set up SVG for D3
var width  = window.innerWidth * 4,
    height = window.innerHeight * 4,
    colors = d3.scale.category10();

window.scrollTo(window.innerWidth * 2, window.innerHeight * 2);

var svg = d3.select('body')
  .append('svg')
  .attr('width', width)
  .attr('height', height);

var nodes = []
var links = []
// var lastNodeId
var currentColor = 0;
var id = 0;

var start_point = "1Aaykbf4iJ8d4UTh2LCjNGZyicqkFresdp"

//classification finder
var classifiers = ["single_use","hot_storage","cold_storage","mining_pool","mining_solo","faucet","distributor","unknown",undefined]
//maps string address to node object
var addressMap = {}
//maps string address to list of string addresses we believe are the same entity
var groupings = {}
//keep track of requested info so we don't do it again
var expand_requests = {}
var applied_expands = {}
var group_requests = {}
// set up initial nodes and links
//  - nodes are known by 'id', not by index in array.
//  - reflexive edges are indicated on the node (as a bold black circle).
//  - links are always source < target; edge directions are set by 'left' and 'right'.

function updateBox(node){
  var group = groupings[node.address];
  if (group === undefined){
    update_aside(node);
    return;
  }
  var addr = {total_received: (node.total_received / 100000.0) + " mBTC", classification: node.classification, label: node.label, balance: (node.balance / 100000.0) + " mBTC", total_sent: (node.total_sent / 100000.0) + " mBTC"};
  var associated = "";
  for (var i = 0; i < group.length; i++){
    associated += group[i];
    if (i < group.length - 1){
      associated += ', ';
    }
  }
  addr.address = associated;
  update_aside(addr);
}

function updateGraph(shouldApply, wasClicked, address, filename){
  if (address in expand_requests){
    if (shouldApply){
      applyGraphUpdates(address);
    }
    if (wasClicked){
      updateBox(addressMap[address]);
    }
    return;
  }
  d3.json(filename, function(error, graph) {
    console.log(graph.nodes);
    // console.log(graph.links);
  var offset = nodes.length;  
  // nodes = graph.nodes;
  // links = graph.links;
  // lastNodeId = graph.nodes.length;
  var newNodes = []
  for (var i = 0; i < graph.nodes.length; i++){
    var tempNode = graph.nodes[i];
    if (tempNode.address in addressMap){
      var old = addressMap[address]
      old.label = tempNode.label;
      old.classification = tempNode.classification;
      old.total_received = tempNode.total_received;
      old.color = classifiers.indexOf(old.classification);
      old.total_sent = tempNode.total_sent;
      old.balance = tempNode.balance;
      old.size = Math.log(old.total_received);
    }
    var c = classifiers.indexOf(tempNode.classification)
    console.log('got a color for a node: ' + c + ', with class: ' + tempNode.classification);
    var newNode = {size: tempNode.size, address: tempNode.address, color: c, id: id, label: tempNode.label, classification: tempNode.classification, total_received: tempNode.total_received, total_sent: tempNode.total_sent, balance: tempNode.balance};
    console.log(newNode);
    id += 1;
    // newNode.size = tempNode.size;
    // newNode.address = tempNode.address;
    // console.log(tempNode.label);
    newNodes.push(newNode);
  }
  // console.log("")
  var newLinks = []
  for (var i = 0; i < graph.links.length; i++){
    var tempLink = graph.links[i];
    // console.log('from: ' + newLink.source.address + ', to: ' + newLink.target.address);
    var newLink = {source:tempLink.source, target:tempLink.target, linkNum:tempLink.linkNum};
    newLinks.push(newLink);
  }
  var data = []
  data.push(newNodes);
  data.push(newLinks);
  expand_requests[address] = data
  currentColor += 1;
  if (shouldApply){
      applyGraphUpdates(address);
  }
  else{
    restart();
  }
  if (wasClicked){
      updateBox(addressMap[address]);
  }
  });
}

function applyGraphUpdates(address){
  if (address in applied_expands){
    return;
  }
  applied_expands[address] = 1;
  console.log(expand_requests);
  // while(expand_requests[address] === undefined){

  // }
  var newNodes = expand_requests[address][0]
  var newLinks = expand_requests[address][1]
  for (var i = 0; i < newNodes.length; i++){
    var tempNode = newNodes[i];
    if(tempNode.address in addressMap){
      if (tempNode.label.length > 0)
      console.log('found a label for ' + tempNode.address);
      // console.log('size for ' + addressMap[tempNode.address].id + ' is going up from ' + addressMap[tempNode.address].size + ' by ' + tempNode.size);
      // addressMap[tempNode.address].size = addressMap[tempNode.address].size + tempNode.size;
      continue;
    }
    addressMap[tempNode.address] = tempNode;
    if (!(tempNode.address in groupings)){
      var group = getGrouping(tempNode.address);
        if (group == null){
          groupings[tempNode.address] = [tempNode.address]
        }
        else{
          groupings[tempNode.address] = group
        }
    }
    console.log("PUSHING");
    console.log(tempNode);
    nodes.push(tempNode);
  }

  for (var i = 0; i < newLinks.length; i++){
    var tempLink = newLinks[i];
    var source = addressMap[newNodes[tempLink.source].address];
    var target = addressMap[newNodes[tempLink.target].address];
    var newLink = {source:source, target:target, linkNum:tempLink.linkNum};

    links.push(newLink);
  }
  console.log(nodes);
  console.log(links);
  restart();
}

function getGrouping(address){
  for (var addr in groupings){
    var others = groupings[addr];
    if (address in others){
      return others;
    }
  }
  return null;
}
updateGraph(true, false, start_point, "data?type=explore&address=" + start_point + "&layers=0&direction=0");
// updateGraph(true, false, "1GD3Sg3xcAzoc4V2SbkdTkFT9acio65Wr9" , "data?type=explore&address=1GD3Sg3xcAzoc4V2SbkdTkFT9acio65Wr9&layers=0&direction=0")
// updateGraph(true, false, "16dJhwTJMgzzwydoB1gsYx4zkdrc4Ue8QY" , "data?type=explore&address=16dJhwTJMgzzwydoB1gsYx4zkdrc4Ue8QY&layers=0&direction=0")
// updateGraph(true, false, "1EruyZfYWniAnw3PiKefTrRafyS4da5SJa" , "data?type=explore&address=1EruyZfYWniAnw3PiKefTrRafyS4da5SJa&layers=0&direction=0")
// updateGraph(true, false, "1NxMkvbYn8o7kKCWPsnWR4FDvH7L9TJqGG" , "data?type=explore&address=1NxMkvbYn8o7kKCWPsnWR4FDvH7L9TJqGG&layers=0&direction=0")
// updateGraph(true, false, "1FA57SXagJUq7zhnk5kTQMQmWSE3eBVbMr" , "data?type=explore&address=1FA57SXagJUq7zhnk5kTQMQmWSE3eBVbMr&layers=0&direction=0")
// updateGraph(true, false, "1MrdjjEhVNoofNMiCbvXEmgrB3K22LxPMd" , "data?type=explore&address=1MrdjjEhVNoofNMiCbvXEmgrB3K22LxPMd&layers=0&direction=0")
// updateGraph(true, false, "1Lcd4bmrSytyDzHYdz7pyx11vrswcERM5k" , "data?type=explore&address=1Lcd4bmrSytyDzHYdz7pyx11vrswcERM5k&layers=0&direction=0")
// updateGraph(true, false, "1cypherEucdwyZ8Xn84M8qUscjBXnWGZA" , "data?type=explore&address=1cypherEucdwyZ8Xn84M8qUscjBXnWGZA&layers=0&direction=0")
// updateGraph(true, false, "1F7XgercyaXeDHiuq31YzrVK5YAhbDkJhf" , "data?type=explore&address=1F7XgercyaXeDHiuq31YzrVK5YAhbDkJhf&layers=0&direction=0")
// updateGraph(true, false, "15woTu5jrfLRtgSmP5YS1rHEWZrLiDmJgE" , "data?type=explore&address=15woTu5jrfLRtgSmP5YS1rHEWZrLiDmJgE&layers=0&direction=0")
// updateGraph(true, false, "15B7QYCSh8MqBMA6b1wtt7n6CsrKdpRDC1" , "data?type=explore&address=15B7QYCSh8MqBMA6b1wtt7n6CsrKdpRDC1&layers=0&direction=0")
// updateGraph(true, false, "1GxKNPRDxT6Wx2EYv5CVz1FWwDDEq6Tmw4" , "data?type=explore&address=1GxKNPRDxT6Wx2EYv5CVz1FWwDDEq6Tmw4&layers=0&direction=0")
// updateGraph(true, false, "1LkTEGGyMKGgSo71f1sEubwG5PSg691zKb" , "data?type=explore&address=1LkTEGGyMKGgSo71f1sEubwG5PSg691zKb&layers=0&direction=0")
// updateGraph(true, false, "1H2BTW6FvWyQAiceePHFYeVnHJboiEWCyR" , "data?type=explore&address=1H2BTW6FvWyQAiceePHFYeVnHJboiEWCyR&layers=0&direction=0")
// updateGraph(true, false, "1HFj8rcMxqDinBdGE4zpGXEMz9Cuqt8iVG" , "data?type=explore&address=1HFj8rcMxqDinBdGE4zpGXEMz9Cuqt8iVG&layers=0&direction=0")
// setTimeout(function(){applyGraphUpdates("13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg")}, 3000);

function updateGroups(address, filename){
  if (address in group_requests){
    return;
  }
  group_requests[address] = 1
  d3.json(filename, function(error, graph) {
    //first update groupings
    var addrs = [];
    for (var i = 0; i < graph.nodes.length; i++){
      addrs.push(graph.nodes[i].address);
    }    
    // console.log(addrs);
    var group = groupings[address];
    for (var i = 0; i < addrs.length; i++){
      if (group.indexOf(addrs[i]) === -1){
        group.push(addrs[i]);
      }
    }
    for (var i = 0; i < group.length; i++){
      groupings[group[i]] = group;
    }
    //now update each node that was affected
    var node = addressMap[address];
    var toRemove = []
    for (var i = 0; i < group.length; i++){
      // console.log("group member: " + group[i]);
      if (group[i] === address){
        continue;
      }
      var addr = group[i];
      if (addr in addressMap){
        var oldNode = addressMap[addr]
        //update map
        addressMap[addr] = node;
        node.size += oldNode.size;
        //update links
        for (var j = 0; j < links.length; j++){
          var link = links[j];
          // console.log(link);
          // console.log("comparing ")
          if (link.source.address === addr){
            if (link.target.address === address){
              toRemove.push(j);
            }
            else{
              link.source = node;
            }
          }
          if (link.target.address === addr){
            // console.log(link);
            if (link.source.address === address){
              toRemove.push(j);
            }
            else{
              link.target = node;
            }
          }
        }
        //update node list
        nodes.splice(nodes.indexOf(oldNode), 1);
      }
    }
    for (var i = 0; i < toRemove.length; i++){
      // console.log("killing with: " + links[i].source.id + " to " + links[i].target.id);
      links.splice(toRemove[i], 1);
    }
    // console.log("====================")
    updateBox(address);
    restart();
  });
}

  

// var nodes = [
//     {id: 0, reflexive: false},
//     {id: 1, reflexive: true },
//     {id: 2, reflexive: false}
//   ],
//   lastNodeId = 2,
//   links = [
//     {source: nodes[0], target: nodes[1], left: false, right: true },
//     {source: nodes[1], target: nodes[2], left: false, right: true }
//   ];

// init D3 force layout
var force = d3.layout.force()
    .nodes(nodes)
    .links(links)
    .size([width, height])
    .linkDistance(150)
    .charge(-500)
    .on('tick', tick)

// define arrow markers for graph links
svg.append('svg:defs').append('svg:marker')
    .attr('id', 'end-arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 6)
    .attr('markerWidth', 3)
    .attr('markerHeight', 3)
    .attr('orient', 'auto')
  .append('svg:path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#000');

svg.append('svg:defs').append('svg:marker')
    .attr('id', 'start-arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 4)
    .attr('markerWidth', 3)
    .attr('markerHeight', 3)
    .attr('orient', 'auto')
  .append('svg:path')
    .attr('d', 'M10,-5L0,0L10,5')
    .attr('fill', '#000');

// line displayed when dragging new nodes
var drag_line = svg.append('svg:path')
  .attr('class', 'link dragline hidden')
  .attr('d', 'M0,0L0,0');

// handles to link and node element groups
var path = svg.append('svg:g').selectAll('path'),
    circle = svg.append('svg:g').selectAll('g');

// mouse event vars
var selected_node = null,
    selected_link = null,
    mousedown_link = null,
    mousedown_node = null,
    mouseup_node = null;

function resetMouseVars() {
  mousedown_node = null;
  mouseup_node = null;
  mousedown_link = null;
}

// update force layout (called automatically each iteration)
function tick() {
  // draw directed edges with proper padding from node centers
  path.attr('d', function(d) {
    var deltaX = d.target.x - d.source.x,
        deltaY = d.target.y - d.source.y,
        dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY),
        normX = deltaX / dist,
        normY = deltaY / dist,
        sourcePadding = d.left ? 17 : 12,
        targetPadding = d.right ? 17 : 12,
        sourceX = d.source.x + (sourcePadding * normX),
        sourceY = d.source.y + (sourcePadding * normY),
        targetX = d.target.x - (targetPadding * normX),
        targetY = d.target.y - (targetPadding * normY);
    return 'M' + sourceX + ',' + sourceY + 'L' + targetX + ',' + targetY;
  });

  circle.attr('transform', function(d) {
    return 'translate(' + d.x + ',' + d.y + ')';
  });
}

function getLabel(d){
  if (d.label.length > 0){
    return d.label;
  }
  var group = groupings[d.address]
  // console.log(group);
  var ret = "";
  for (var i = 0; i < group.length; i++){
    ret += group[i];
    if (i < group.length - 1){
      ret += "\n";
    }
  }
  // console.log(d.address + '\nnow /comes the ret\n' + ret);
  // console.log("...");
  return ret;
}

// update graph (called when needed)
function restart() {
  // console.log(nodes);
  // path (link) group
  path = path.data(links);

  // for (var i = 0; i < nodes.length; i++){
  //   console.log(nodes[i]);
  // }

  // for (var i = 0; i < links.length; i++){
  //   console.log(links[i]);
  // }

  // update existing links
  path.classed('selected', function(d) { return d === selected_link; });
    // .style('marker-start', function(d) { return d.left ? 'url(#start-arrow)' : ''; })
    // .style('marker-end', function(d) { return d.right ? 'url(#end-arrow)' : ''; });


  // add new links
  path.enter().append('svg:path')
    .attr('class', 'link')
    .classed('selected', function(d) { return d === selected_link; })
    // .style('marker-start', function(d) { return d.left ? 'url(#start-arrow)' : ''; })
    // .style('marker-end', function(d) { return d.right ? 'url(#end-arrow)' : ''; })
    .on('mousedown', function(d) {
      if(d3.event.ctrlKey) return;

      // select link
      mousedown_link = d;
      if(mousedown_link === selected_link) selected_link = null;
      else selected_link = mousedown_link;
      selected_node = null;
      restart();
    });

  // remove old links
  path.exit().remove();


  // circle (node) group
  // NB: the function arg is crucial here! nodes are known by id, not by index!
  circle = circle.data(nodes, function(d) { return d.address; });

  // update existing nodes (reflexive & selected visual states)
  circle.selectAll('circle')
    .style('fill', function(d) { return (d === selected_node) ? d3.rgb(colors(d.color)).brighter().toString() : colors(d.color); })
    .style('stroke', function(d) { return d3.rgb(colors(d.color)).darker().toString(); })
    .attr('r', function(d){ return d.size })
    .append("title")
        .text(function(d){
          return getLabel(d);
        });
    // .classed('reflexive', function(d) { return d.reflexive; });

    // circle

  // add new nodes
  var g = circle.enter().append('svg:g');

  g.append('svg:circle')
    .attr('class', 'node')
    .attr('r', function(d){ return d.size })
    .style('fill', function(d) { return (d === selected_node) ? d3.rgb(colors(d.color)).brighter().toString() : colors(d.color); })
    .style('stroke', function(d) { return d3.rgb(colors(d.color)).darker().toString(); })
    // .classed('reflexive', function(d) { return d.reflexive; })
    .on('mouseover', function(d) {
      // if(!mousedown_node || d === mousedown_node){
        // return;
      // }
      // enlarge target node
      d3.select(this).attr('transform', 'scale(1.2)');
    })
    .on('mouseout', function(d) {
      // if(!mousedown_node || d === mousedown_node) return;
      // unenlarge target node
      d3.select(this).attr('transform', '');
    })
    .on('mousedown', function(d) {
      if(d3.event.ctrlKey) return;

      // select node
      mousedown_node = d;
      // if(mousedown_node === selected_node) selected_node = null;
      selected_node = mousedown_node;
      updateGraph(false, true, d.address, "data?type=explore&address=" + d.address + "&layers=0&direction=0");
      selected_link = null;

      // reposition drag line
      // drag_line
        // .style('marker-end', 'url(#end-arrow)')
        // .classed('hidden', false)
        // .attr('d', 'M' + mousedown_node.x + ',' + mousedown_node.y + 'L' + mousedown_node.x + ',' + mousedown_node.y);

      restart();
    })
    .on('mouseup', function(d) {
      if(!mousedown_node) return;

      // needed by FF
      drag_line
        .classed('hidden', true)
        .style('marker-end', '');

      // check for drag-to-self
      mouseup_node = d;
      if(mouseup_node === mousedown_node) { resetMouseVars(); return; }

      // unenlarge target node
      d3.select(this).attr('transform', '');

      // add link to graph (update if exists)
      // NB: links are strictly source < target; arrows separately specified by booleans
      // var source, target, direction;
      // if(mousedown_node.id < mouseup_node.id) {
      //   source = mousedown_node;
      //   target = mouseup_node;
      //   direction = 'right';
      // } else {
      //   source = mouseup_node;
      //   target = mousedown_node;
      //   direction = 'left';
      // }

      // var link;
      // link = links.filter(function(l) {
      //   return (l.source === source && l.target === target);
      // })[0];

      // if(link) {
      //   link[direction] = true;
      // } else {
      //   link = {source: source, target: target, left: false, right: false};
      //   link[direction] = true;
      //   links.push(link);
      // }

      // // select new link
      // selected_link = link;
      // selected_node = null;
      restart();
    });

        g.append("svg:title")
        .text(function(d){
          return getLabel(d);
        })

  // show node IDs
  g.append('svg:text')
      .attr('x', 0)
      .attr('y', 4)
      .attr('class', 'id')
      .text(function(d) { return d.id; });

  // remove old nodes
  circle.exit().remove();

  // set the graph in motion
  force.start();
}



// function mousedown() {
//   alert('hi');
//   // prevent I-bar on drag
//   //d3.event.preventDefault();
  
//   // because :active only works in WebKit?
//   svg.classed('active', true);

//   if(d3.event.ctrlKey || mousedown_node || mousedown_link) return;

//   // insert new node at point
//   var point = d3.mouse(this),
//       node = {id: ++lastNodeId, reflexive: false};
//   node.x = point[0];
//   node.y = point[1];
//   nodes.push(node);

//   restart();
// }

// function mousemove() {
//     alert('hi');
//   if(!mousedown_node) return;

//   // update drag line
//   drag_line.attr('d', 'M' + mousedown_node.x + ',' + mousedown_node.y + 'L' + d3.mouse(this)[0] + ',' + d3.mouse(this)[1]);

//   restart();
// }

// function mouseup() {
//     alert('hi');
//   if(mousedown_node) {
//     // hide drag line
//     drag_line
//       .classed('hidden', true)
//       .style('marker-end', '');
//   }

//   // because :active only works in WebKit?
//   svg.classed('active', false);

//   // clear mouse event vars
//   resetMouseVars();
// }

function spliceLinksForNode(node) {
  var toSplice = links.filter(function(l) {
    return (l.source === node || l.target === node);
  });
  toSplice.map(function(l) {
    links.splice(links.indexOf(l), 1);
  });
}

// only respond once per keydown
var lastKeyDown = -1;

function keydown() {

  if(lastKeyDown !== -1) return;
  lastKeyDown = d3.event.keyCode;

  if (d3.event.keyCode == 32){
    d3.event.preventDefault();
    window.scrollTo(window.innerWidth * 1.5, window.innerHeight * 1.5);
    return;
  }

  // ctrl
  if(d3.event.keyCode === 17) {
    circle.call(force.drag);
    svg.classed('ctrl', true);
  }

  if(!selected_node && !selected_link) return;
  switch(d3.event.keyCode) {
    case 73:
      // alert('pressed space');
      //prompt("Copy me!",selected_node.address);
      d3.event.preventDefault(); 
      window.open("https://blockchain.info/address/"+selected_node.address);
      break;
    // case 8: // backspace
    // case 46: // delete
    //   if(selected_node) {
    //     nodes.splice(nodes.indexOf(selected_node), 1);
    //     spliceLinksForNode(selected_node);
    //   } else if(selected_link) {
    //     links.splice(links.indexOf(selected_link), 1);
    //   }
    //   selected_link = null;
    //   selected_node = null;
    //   restart();
    //   break;
    case 69: //E
      d3.event.preventDefault();
      var addr = selected_node.address;
      var json = "data?type=explore&address=" + addr + "&layers=0&direction=1";
      updateGraph(true, false, addr, json);
      applyGraphUpdates(addr);
      break;
    case 71: //G
      d3.event.preventDefault();
      var addr = selected_node.address;
      var json = "data?type=entity&address=" + addr + "&max_nodes=10&direction=0"
      updateGroups(addr, json);
      break;
    // case 66: // B
    //   if(selected_link) {
    //     // set link direction to both left and right
    //     selected_link.left = true;
    //     selected_link.right = true;
    //   }
    //   restart();
    //   break;
    // case 76: // L
    //   if(selected_link) {
    //     // set link direction to left only
    //     selected_link.left = true;
    //     selected_link.right = false;
    //   }
    //   restart();
    //   break;
    // case 82: // R
    //   if(selected_node) {
    //     // toggle node reflexivity
    //     selected_node.reflexive = !selected_node.reflexive;
    //   } else if(selected_link) {
    //     // set link direction to right only
    //     selected_link.left = false;
    //     selected_link.right = true;
    //   }
    //   restart();
    //   break;
  }
}

function keyup() {
  lastKeyDown = -1;

  // ctrl
  if(d3.event.keyCode === 17) {
    circle
      .on('mousedown.drag', null)
      .on('touchstart.drag', null);
    svg.classed('ctrl', false);
  }
}

// app starts here
// svg.on('mousedown', mousedown)
//   .on('mousemove', mousemove)
//   .on('mouseup', mouseup);
d3.select(window)
  .on('keydown', keydown)
  .on('keyup', keyup);

// });
