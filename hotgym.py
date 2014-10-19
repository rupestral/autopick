#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""A simple client to create a CLA model for hotgym."""

import csv
import datetime
import time
import logging

from nupic.data.datasethelpers import findDataset
from nupic.frameworks.opf.metrics import MetricSpec
from nupic.frameworks.opf.modelfactory import ModelFactory
from nupic.frameworks.opf.predictionmetricsmanager import MetricsManager
import py2neo

import model_params

from py2neo import neo4j

graph_db = neo4j.GraphDatabaseService()
graph_db.clear();



query = neo4j.CypherQuery(graph_db, "CREATE (a {name:{name_a}})-[ab:KNOWS]->(b {name:{name_b}})"
                              "RETURN a, b, ab")
a, b, ab = query.execute(name_a="Alice", name_b="Bob").data[0]

print a, b, ab

query = neo4j.CypherQuery(graph_db, "MATCH (a)-[r]-(b) RETURN a,r,b")

result = query.execute_one()

print result[2]


query = neo4j.CypherQuery(graph_db,"MATCH (a)-[r]-(b) RETURN a,r,b")
for record in query.stream():
    print record[0], record[1],record[2]

###################

_LOGGER = logging.getLogger(__name__)

_DATA_PATH = "extra/hotgym/rec-center-hourly.csv"

_METRIC_SPECS = (
    MetricSpec(field='consumption', metric='multiStep',
               inferenceElement='multiStepBestPredictions',
               params={'errorMetric': 'aae', 'window': 1000, 'steps': 1}),
    MetricSpec(field='consumption', metric='trivial',
               inferenceElement='prediction',
               params={'errorMetric': 'aae', 'window': 1000, 'steps': 1}),
    MetricSpec(field='consumption', metric='multiStep',
               inferenceElement='multiStepBestPredictions',
               params={'errorMetric': 'altMAPE', 'window': 1000, 'steps': 1}),
    MetricSpec(field='consumption', metric='trivial',
               inferenceElement='prediction',
               params={'errorMetric': 'altMAPE', 'window': 1000, 'steps': 1}),
)

_NUM_RECORDS = 10



def createModel():
  return ModelFactory.create(model_params.MODEL_PARAMS)



def runHotgym():
  model = createModel()
  model.enableInference({'predictedField': 'consumption'})
  metricsManager = MetricsManager(_METRIC_SPECS, model.getFieldInfo(),
                                  model.getInferenceType())
  with open (findDataset(_DATA_PATH)) as fin:
    reader = csv.reader(fin)
    headers = reader.next()
    print headers[0], headers[1]
    record = reader.next()
    print record
    record = reader.next()
    print record
    record1 = reader.next()
    timestamp1 = time.mktime(datetime.datetime.strptime(record1[0], "%y/%d/%m %H:%M").timetuple())
    print timestamp1
    record2 = reader.next()
    print record2[0], record2[1]
    print record2[0]-record1[0]
    for i, record in enumerate(reader, start=1):
      modelInput = dict(zip(headers, record))
      modelInput["consumption"] = float(modelInput["consumption"])
      modelInput["timestamp"] = datetime.datetime.strptime(
          modelInput["timestamp"], "%m/%d/%y %H:%M")
      result = model.run(modelInput)
      #print result
      #import sys; sys.exit()
      result.metrics = metricsManager.update(result)
      isLast = i == _NUM_RECORDS
      if i % 10 == 0 or isLast:
        _LOGGER.info("After %i records, 1-step altMAPE=%f", i,
                    result.metrics["multiStepBestPredictions:multiStep:"
                                   "errorMetric='altMAPE':steps=1:window=1000:"
                                   "field=consumption"])
      if isLast:
        break



if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  runHotgym()
