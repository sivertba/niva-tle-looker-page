# README

This script generates a forecast of satellite passes for the next week. The forecast is generated using the pyorbital library and is updated every day. The cloud cover is retrieved from the Norwegian Meteorological Institute. The cloud cover is given as the median of a grid at the location.

## Usage

The script ´pass_computer.py´ can be run from the command line with the following arguments:

- `--debug`: Print debug information
- `--look_ahead_hrs`: How many hours to look ahead (default: 24 * 6)
- `--minelev`: Minimum elevation for passes (default: 40.0)
- `--maxclouds`: Maximum cloud cover for passes (default: 50.0)
- `--gitupload`: Upload to github (default: False)
- `--verbose`: Print verbose information (default: False)

## Output

The script generates an HTML file named `index.html` containing the forecast of satellite passes for the next week. The HTML file contains a table of locations and a table of satellites used in the forecast.

## Dependencies

The script requires the following dependencies:

- pyorbital
- pandas
- numpy
- requests
- pypandoc
- argparse
- json
- datetime
- os

## License

This script is licensed under the MIT License. See the LICENSE file for more information.
