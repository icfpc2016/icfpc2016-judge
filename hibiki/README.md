Hibiki - Judge Frontend
=======================

This is the server program used to accept submissions for
ICPC Programming Contest 2016 (http://2016.icfpcontest.org).


Required Dependencies
---------------------

- Linux amd64 (preferably Ubuntu 14.04+)
- Python 2.7 + pip + virtualenv
- MongoDB 3.0+


About Prebuilt Binary
---------------------

`app/prebuilts/akatsuki` is a prebuilt binary compiled for Linux amd64.
If you try to run the server in other environments, you need to build it
by yourself.


How to Run the Server
---------------------

Ensure mongodb server is running locally with authentication disabled. Then run:

```
$ ./run_devserver.sh
```

This command may take several minutes on the first run to install dependencies.

Then you can access the server at http://localhost:8080.
