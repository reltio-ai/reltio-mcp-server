#!/bin/bash
# Simple script to run tests for the Reltio MCP Server

# Set default values
COVERAGE=0
VERBOSE=0
TEST_PATH="tests"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -c|--coverage)
      COVERAGE=1
      shift
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -p|--path)
      TEST_PATH="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-c|--coverage] [-v|--verbose] [-p|--path TEST_PATH]"
      exit 1
      ;;
  esac
done

# Build the pytest command
CMD="python -m pytest"

# Add options based on command line arguments
if [ $VERBOSE -eq 1 ]; then
  CMD="$CMD -v"
fi

if [ $COVERAGE -eq 1 ]; then
  CMD="$CMD --cov=src --cov-report=term-missing"
fi

# Add the test path
CMD="$CMD $TEST_PATH"

# Print the command being run
echo "Running: $CMD"

# Run the tests
eval $CMD

# Exit with the pytest exit code
exit $?