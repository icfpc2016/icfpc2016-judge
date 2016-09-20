Akatsuki - Judge Backend
========================

This is the program used to evaluate origami submissions for
ICPC Programming Contest 2016 (http://2016.icfpcontest.org).


Required Dependencies
---------------------

- gmp (https://gmplib.org/)
- gflags (https://github.com/gflags/gflags)
- glog (https://github.com/google/glog)

Please use GCC. Clang will not work (due to `std::complex` undefined behavior).


How to Build and Use
--------------------

```
$ make
$ ./akatsuki --help
$ ./akatsuki --compile solution.txt
$ ./akatsuki --evaluate problem.txt solution.txt
```
