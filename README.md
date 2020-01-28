# LetGo

LetGo offers the users the prototype of the roll-forward recovery system for HPC applications.  


## Files explained

configure.py - to setup the application configurations 

faultinject.py - to handle the fault injection experiment functions

sighandler.py - the main LetGo implementation

letgo_wrapper.py - the wrapper to launch fault injections and applications with LetGo

### Prerequisites

Please use https://github.com/flyree/pb_interceptor to build the Pintool


## Running the tests

python letgo_wrapper.py 

## Authors

* **Bo Fang** - *Initial work*


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
