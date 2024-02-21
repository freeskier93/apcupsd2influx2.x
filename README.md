# apcupsd2influx2.x

Docker image that will collect UPS telemetry data and export it to InfluxDB 2.x (NOT compatible with InfluxDB 1.x). UPS data is collected from [APCUPSD](http://www.apcupsd.org/) using the [apcaccess](https://pypi.org/project/apcaccess/) Python library.

This container also fixes issues with future datatype conflicts because datatypes are strictly defined. In particular, trying to infer UPS serial number datatype can cause serious issues with InfluxDB since you can't delete/modify fields. Some UPSs may be all numbers the data is converted to an integer/float, while other UPSs may have letters so they get converted to strings. If this happens (say when changing UPSs) it will cause errors when writing the data to Influx.

## Environment Variables

| Environment Variable | Default Value | Description |
| -------------------- | ------------- | ----------- |
| APCUPSD_HOST | 127.0.0.1 | Hostname/IP where APCUPSD is running |
| APCUPSD_PORT | 3551 | Port that APCUPSD is listening on |
| APCUPSD_POLL_RATE | 5 | Rate to poll data from UPS (seconds) WARNING: Poll rate affects how energy (kWh) and costs are calculated |
| APCUPSD_NOMINAL_POWER | 0 | Nominal power rating of your UPS, required if your UPS does not report NOMPOWER value (watts) |
| INFLUXDB_HOST | 127.0.0.1 | Hostname/IP where InfluxDB is running |
| INFLUXDB_PORT | 8086 | Port InfluxDB is listening on |
| INFLUXDB_TOKEN | None | InfluxDB token, this is required |
| INFLUXDB_BUCKET | apcupsd | Name of the bucket data will be saved to |
| INFLUXDB_MEASUREMENT | ups_telemetry | Name of the measurement data will be save to in the bucket |
| INFLUXDB_ORG | homelab | Optional organization name |
| DEBUG | false | Enable/Disable Debug logging (true/false) |

## How to Use

### Prerequisites
* APCUPSD must be installed/running somewhere and connected to a UPS. 
* InfluxDB 2.x is running (InfluxDB 1.x is NOT compatible).

### Creating InfluxDB Token
If you do not already have an InfluxDB token use the following steps to create one [Create a Token in the InfluxDB UI](https://docs.influxdata.com/influxdb/v2/admin/tokens/create-token/#create-a-token-in-the-influxdb-ui)

### Run Docker Container
```bash
docker run --rm  -d --name="apcupsd2influx2.x" \
    -e "APCUPSD_HOST=192.168.1.10" \
    -e "INFLUXDB_HOST=192.168.1.10" \
    -e "INFLUXDB_TOKEN=<token>" \
    -t freeskier93/apcupsd2influx2.x
```
Note: If your UPS does not include the NOMPOWER point, you will need to include the APCUPSD_NOMINAL_POWER environment variable in order to calculate the power consumption. If you do not define this value, and your UPS does not send the value, then it will default to 0 and calculated power will be 0.

### Connecting Grafana to InfluxDB 2.x
InfluxDB 2.x supports the older InfluxQL language for querying data, this is the recommended way to connect to the InfluxDB instead of the newer Flux language. Reference the following Influx documentation [Configure your InfluxDB Connection](https://docs.influxdata.com/influxdb/v2/tools/grafana/#configure-your-influxdb-connection). The database name used should match the bucket name, which is "apcupsd" by default. If you set the INFLUXDB_BUCKET variable to something else you need to use that for the database name.

The default measurement name is "ups_telemetry". Some of the existing Grafana dashboards,such as [Unraid UPS Dashboard v2.0 TR](https://grafana.com/grafana/dashboards/10615-unraid-ups-dashboard-v2-0-tr/), expect a different measurement name when performing the queries. Set the INFLUXDB_MEASUREMENT variable to match whatever the dashboard expects.

The rate rate at which data is polled from the UPS affects how total energy (kWh) and cost is calculated. If you adjust APCUPSD_POLL_RATE you must also update any Grafana dashboards to use the correct value when calculating energy and cost.
