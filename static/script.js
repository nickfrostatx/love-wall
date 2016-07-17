var container = d3.select('.container');
  var svg = d3.select('svg');
  var map = svg.insert('svg:path')
  .attr('class', 'map');
  var locations = svg.insert('svg:g');

  function draw(events) {
  // Contain in div, preserve 3/2 aspect ratio
  var parentWidth = parseInt(container.style('width')),
    parentHeight = parseInt(container.style('height')),
    ratio = 3/2, width, height;

  if (parentWidth > ratio * parentHeight) {
    height = parentHeight;
    width = height * ratio;
  } else {
    width = parentWidth;
    height = width / ratio;
  }

  svg.attr('width', width);
  svg.attr('height', height);

  var projection = d3.geoMercator()
    .scale(width / 2 / Math.PI)
    .translate([width * .5, height * .7])
    .rotate([-12, 0, 0]);

  var path = d3.geoPath()
    .projection(projection);

  map.attr('d', path);

  var toTransform = function(evt) {
    var loc = projection(evt.location.coords);
    return 'translate(' + loc[0] + ',' + loc[1] + ')';
  }

  var locationGroups = locations.selectAll('g')
      .attr('transform', toTransform)
    .data(events)
    .enter().append('svg:g')
      .attr('transform', toTransform);

  locationGroups.append('svg:circle')
    .attr('class', 'location-dot')
    .attr('r', 3)
    .attr('cx', 0)
    .attr('cy', 0);

  locationGroups.append('svg:line')
    .attr('class', 'location-line')
    .attr('x1', 0)
    .attr('y1', 0)
    .attr('x2', -5)
    .attr('y2', -15);

  locationGroups.append('svg:text')
    .attr('class', 'location-name')
    .attr('y', -19)
    .attr('text-anchor', 'middle')
    .text(function(evt) { return evt.location.name });
}

function makeRequests(urls) {
  var getJsonUrl = function(url) {
    return new Promise(function(resolve, reject) {
      d3.json(url, function(error, data) {
        if (error) {
          reject(error);
        } else {
          resolve(data);
        }
      });
    });
  };
  return Promise.all(urls.map(getJsonUrl));
}

makeRequests(['/static/world.json', '/events'])
  .then(function(values) {
    var world = values[0], events = values[1];

    map.datum(topojson.feature(world, world.objects.subunits))

    window.addEventListener('resize', function() { draw(events) });
    window.addEventListener('scroll', function() { draw(events) });
    draw(events.events);
  });
