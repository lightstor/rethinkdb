#!/usr/bin/env python
# Copyright 2010-2014 RethinkDB, all rights reserved.
import sys, os, time, datetime, socket, pprint
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, 'common')))
import driver, scenario_common, utils
r = utils.import_python_driver()
from vcoptparse import *

op = OptParser()
scenario_common.prepare_option_parser_mode_flags(op)
opts = op.parse(sys.argv)

with driver.Metacluster() as metacluster:
    cluster = driver.Cluster(metacluster)
    executable_path, command_prefix, serve_options = \
        scenario_common.parse_mode_flags(opts)
    print "Spinning up two processes..."
    files1 = driver.Files(
        metacluster, db_path = "db-1", log_path = "create-output-1",
        server_name = "a", server_tags = ["foo"],
        executable_path = executable_path, command_prefix = command_prefix)
    files2 = driver.Files(
        metacluster, db_path = "db-2", log_path = "create_output-2",
        server_name = "b", server_tags = ["foo", "bar"],
        executable_path = executable_path, command_prefix = command_prefix)
    process1 = driver.Process(cluster, files1, log_path="serve-output-1",
        executable_path = executable_path, command_prefix = command_prefix,
        extra_options = serve_options)
    time.sleep(3)
    process2 = driver.Process(cluster, files2, log_path="serve-output-2",
        executable_path = executable_path, command_prefix = command_prefix,
        extra_options = serve_options)
    process1.wait_until_started_up()
    process2.wait_until_started_up()
    cluster.check()
    reql_conn1 = r.connect("localhost", process1.driver_port)
    reql_conn2 = r.connect("localhost", process2.driver_port)

    def wait_for(predicate):
        for i in xrange(10):
            if predicate():
                break
            time.sleep(1)
        else:
            raise ValueError("Condition not satisfied after 10 seconds")

    assert r.db("rethinkdb").table("server_status").count().run(reql_conn1) == 2
    assert set(r.db("rethinkdb").table("server_status")["name"].run(reql_conn1)) == \
        set(["a", "b"])
    def get_status(name):
        return r.db("rethinkdb").table("server_status").filter({"name":name}).nth(0) \
                .run(reql_conn1)

    st = get_status("a")
    print "Status for a connected server:"
    pprint.pprint(st)

    assert st["status"] == "available"

    assert isinstance(st["process"]["version"], basestring)
    assert st["process"]["version"].startswith("rethinkdb")

    assert st["process"]["pid"] == process1.process.pid

    assert isinstance(st["process"]["cache_size_mb"], int)
    assert st["process"]["cache_size_mb"] < 1024*100

    assert st["network"]["hostname"] == socket.gethostname()
    assert st["network"]["reql_port"] == process1.driver_port
    assert st["network"]["cluster_port"] == process1.cluster_port
    assert st["network"]["http_admin_port"] == process1.http_port
    assert st["network"]["canonical_addresses"][0]["port"] == process1.cluster_port

    now = datetime.datetime.now(st["process"]["time_started"].tzinfo)
    assert st["process"]["time_started"] <= now
    assert st["process"]["time_started"] > now - datetime.timedelta(minutes=1)
    assert st["connection"]["time_connected"] <= now
    assert st["connection"]["time_connected"] >= st["process"]["time_started"]
    assert st["connection"]["time_disconnected"] is None

    assert get_status("b")["status"] == "available"
    process2.check_and_stop()
    wait_for(lambda: get_status("b")["status"] == "unavailable")
    st2 = get_status("b")
    print "Status for a disconnected server:"
    pprint.pprint(st2)

    now = datetime.datetime.now(st2["connection"]["time_disconnected"].tzinfo)
    assert st2["connection"]["time_connected"] is None
    assert st2["connection"]["time_disconnected"] <= now
    assert st2["connection"]["time_disconnected"] >= now - datetime.timedelta(minutes=1)

    cluster.check_and_stop()

