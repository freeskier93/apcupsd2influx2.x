#!/usr/bin/python
import os
import sys
import time
import logging
import pprint

from datetime import datetime, UTC

from constants import DATA_TYPES, REMOVE_KEYS, TAG_KEYS

from apcaccess import status as apc
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)
logger.setLevel(level="INFO")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)

if __name__ == "__main__":

    apcupsd_host = str(os.getenv("APCUPSD_HOST"))
    apcupsd_port = int(os.getenv("APCUPSD_PORT", 3551))
    apcupsd_poll_rate = int(os.getenv("APCUPSD_POLL_RATE", 5))
    apcupsd_nominal_power = int(os.getenv("APCUPSD_NOMINAL_POWER", 0))

    influx_host = str(os.getenv("INFLUXDB_HOST"))
    influx_port = int(os.getenv("INFLUXDB_PORT", 8086))
    influx_token = str(os.getenv("INFLUXDB_TOKEN"))
    influx_bucket = str(os.getenv("INFLUXDB_BUCKET", "apcupsd"))
    influx_measurement = str(os.getenv("INFLUXDB_MEASUREMENT", "ups_telemetry"))
    influx_org = str(os.getenv("INFLUXDB_ORG", "homelab"))

    if os.getenv("DEBUG", "false").lower() == "true":
        logger.setLevel("DEBUG")

    if not apcupsd_host:
        logger.error("APCUPSD_HOST not set")
        sys.exit()

    if not influx_host:
        logger.error("INFLUXDB_HOST not set")
        sys.exit()

    if not influx_token:
        logger.error("INFLUX_TOKEN not set")
        sys.exit()

    logger.info(f"APCUPSD Host: {apcupsd_host}")
    logger.info(f"APCUPSD_PORT: {apcupsd_port}")
    logger.info(f"APCUPSD Poll Rate: {apcupsd_poll_rate} seconds")
    logger.info(f"Influx Host: {influx_host}")
    logger.info(f"Influx Port: {influx_port}")
    logger.info(f"Influx Bucket Name: {influx_bucket}")
    logger.info(f"Influx Measurement Name: {influx_measurement}")
    logger.info(f"Influx Organization Name: {influx_org}")

    influx_url = f"http://{influx_host}:{influx_port}"
    logger.debug(f"Influx URL: {influx_url}")

    influx_client = None

    while True:

        # Create InfluxDB client. From this the bucket API can be created for adding a new bucket
        # and the write API can be created for writing to the database
        if not influx_client:
            try:
                influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
            except Exception as e:
                logger.error("Could not create InfluxDB client")
                logger.exception(e)

            logger.info("Pinging InfluxDB...")
            if not influx_client.ping():
                logger.error(f"Could not connect to InfluxDB at {influx_url}. Resetting client and trying again.")
                influx_client = None
                time.sleep(apcupsd_poll_rate)
                continue

            logger.info("Successfully connected to InfluxDB")

            buckets_api = influx_client.buckets_api()
            if not buckets_api.find_bucket_by_name(influx_bucket):
                logger.info(f"Bucket '{influx_bucket}' does not exist, creating it")
                try:
                    buckets_api.create_bucket(bucket_name=influx_bucket)
                except Exception as e:
                    logger.error(f"Could not create new bucket: {influx_bucket}")
                    logger.exception(e)

            write_api = influx_client.write_api(write_options=SYNCHRONOUS)

            logger.info("Running data export")

        # Get ups telemetry data
        try:
            logger.debug("Getting data from APCUPSD...")
            ups_tlm = apc.parse(apc.get(host=apcupsd_host, port=apcupsd_port), strip_units=True)
            logger.debug(f"Got data from APCUPSD:\n{pprint.pformat(ups_tlm)}")
        except TimeoutError as e:
            logger.error(f"Could not connect to APCUPSD host due to timeout: {apcupsd_host}")
            time.sleep(apcupsd_poll_rate)
            continue
        except ConnectionRefusedError as e:
            logger.error(f"Could not connect to APCUPSD host because connection was refused: {apcupsd_host}")
            time.sleep(apcupsd_poll_rate)
            continue

        # Generate fields dictionary and tags dictionary
        fields_dict = {}
        tags_dict = {}
        for var in ups_tlm:
            if var in REMOVE_KEYS:
                continue
            if var in DATA_TYPES:
                val = DATA_TYPES[var](ups_tlm[var])
                if var in TAG_KEYS:
                    tags_dict[var] = val
                else:
                    fields_dict[var] = val

        # Set nominal power from ups data, if nominal power is not sent then it defaults to the user specified value
        apcupsd_nominal_power = fields_dict.get("NOMPOWER", apcupsd_nominal_power)

        # If user did not specificy nominal power either then print error
        if apcupsd_nominal_power == 0:
            logger.error("Your UPS does not send NOMPOWER value, you must set APCUPSD_NOMINAL_POWER in the template")

        fields_dict["WATTS"] = int(apcupsd_nominal_power * fields_dict.get("LOADPCT", 0) * 0.01)

        logger.debug(f"Tags dictionary:\n{pprint.pformat(tags_dict)}")
        logger.debug(f"Fields dictionary:\n{pprint.pformat(fields_dict)}")

        time_str = str(datetime.now(UTC))

        # Write data to InfluxDB
        try:
            logger.debug("Writing data to InfluxDB")
            write_api.write(
                bucket=influx_bucket,
                record={
                    "measurement": influx_measurement,
                    "tags": tags_dict,
                    "fields": fields_dict,
                    "time": time_str,
                },
            )
            logger.debug("Data written to InfluxDB")
        except Exception as e:
            logger.error("Could not write data to InfluxDB")
            logger.exception(e)

        time.sleep(apcupsd_poll_rate)
