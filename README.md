# apcupsd2influx2.x

Docker image that will collect UPS telemetry data and export it to InfluxDB 2.x (NOT compatible with InfluxDB 1.x). UPS data is collected from [APCUPSD](http://www.apcupsd.org/) using the [apcaccess](https://pypi.org/project/apcaccess/) Python library.

This script also prevents issues with future datatype conflicts because datatypes are strictly defined. In particular, trying to infer UPS serial number datatype can cause issues when channging UPSs. Some UPSs may use all numbers where some may have numbers and letters. In the case of all numbers it would be identified as a float, but if it has letteres it would be identified as a string. If you change UPSs and go from float to string this will cause errors when writing the data to Influx due to datatype mismatch.

## TODO
- [x] Perform energy consumption calculation and provide it as a field called ENERGY
- [x] Allow user to give cost per kWh and calculate costs, then provide that as a field called COST
- [ ] Allow user to provide a config file that defines cost per kWh for various time ranges that way costs can be calculated for Time of Use

## Environment Variables

| Environment Variable | Default Value | Description |
| -------------------- | ------------- | ----------- |
| APCUPSD_HOST | 127.0.0.1 | Hostname/IP where APCUPSD is running |
| APCUPSD_PORT | 3551 | Port that APCUPSD is listening on |
| APCUPSD_POLL_RATE | 5 | Rate to poll data from UPS (seconds) WARNING: Poll rate may affect how energy consumption (kWh) and costs are calculated, see section below regarding poll rate |
| APCUPSD_NOMINAL_POWER | 0 | Nominal power rating of your UPS, required if your UPS does not report NOMPOWER value (watts) |
| INFLUXDB_HOST | 127.0.0.1 | Hostname/IP where InfluxDB is running |
| INFLUXDB_PORT | 8086 | Port InfluxDB is listening on |
| INFLUXDB_TOKEN | None | InfluxDB token, this is required |
| INFLUXDB_BUCKET | apcupsd | Name of the bucket data will be saved to |
| INFLUXDB_MEASUREMENT | ups_telemetry | Name of the measurement data will be save to in the bucket |
| INFLUXDB_ORG | homelab | Optional organization name |
| DEBUG | false | Enable/Disable Debug logging (true/false) |

## Derived Data
The following data points are derived from the APCUPSD data and available for use

| Variable Name | Description |
| ------------- | ----------- |
| POWER | Calculated power draw in watts |
| ENERGY | Calculated energy consumption in kWh |
| COST | Calculated cost per kWh |

## How to Use

### Prerequisites
* APCUPSD must be installed/running somewhere and connected to a UPS. 
* InfluxDB 2.x is running (InfluxDB 1.x is NOT compatible).

### Creating InfluxDB Token
If you do not already have an InfluxDB token use the following steps to create one [Create a Token in the InfluxDB UI](https://docs.influxdata.com/influxdb/v2/admin/tokens/create-token/#create-a-token-in-the-influxdb-ui)

### Run Docker Container
```bash
docker run --rm -d --name="apcupsd2influx2.x" -e "APCUPSD_HOST=192.168.1.10" -e "INFLUXDB_HOST=192.168.1.10" -e "INFLUXDB_TOKEN=<token>" ghcr.io/freeskier93/apcupsd2influx2.x:latest
```
Note: If your UPS does not include the NOMPOWER point, you will need to include the APCUPSD_NOMINAL_POWER environment variable in order to calculate the power consumption. If you do not define this value, and your UPS does not send the value, then it will default to 0 and calculated power will be 0.

### Connecting Grafana to InfluxDB 2.x
InfluxDB 2.x supports the older InfluxQL language for querying data, this is the recommended way to connect to the InfluxDB instead of the newer Flux language. Reference the following Influx documentation (make sure to select the InfluxQL tab) [Configure your InfluxDB Connection](https://docs.influxdata.com/influxdb/v2/tools/grafana/#configure-your-influxdb-connection). The database name used should match the bucket name, which is "apcupsd" by default. If you set the INFLUXDB_BUCKET variable to something else you need to use that for the database name.

I have made a compatible Grafana dashboard that can be found here: [APCUPSD Data](https://grafana.com/grafana/dashboards/20547-ups-data/)

### Data Poll Rate and Energy Consumption
The rate at which data is polled from the UPS may affect how some Grafana dashboards calculate energy consumption (kWh), which also affects costs. Some dashboards calculate energy consumption by adding all the power values in a time range togehter, then dividing by the measurment time interval. This only works if the time interval they are dividing by actually matches the rate at which data is polled from APCUPSD. If these values don't match, calucalated power consumption will be incorrect. 

This script provides the calculated energy for each time interval, so all you need to do in Grafana is sum the ENERGY field to get total energy for a given time period.
