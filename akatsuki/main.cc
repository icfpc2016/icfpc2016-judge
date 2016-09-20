// -*- mode: c++ -*-
//
// Copyright 2016 ICFP Programming Contest 2016 Organizers
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <fstream>
#include <iostream>

#include <gflags/gflags.h>
#include <glog/logging.h>
#include <gmpxx.h>

#include "compiler.h"
#include "evaluator.h"
#include "problem.h"
#include "solution.h"
#include "validator.h"

DEFINE_bool(compile, false, "Mode flag: compiles a solution to a problem.");
DEFINE_bool(evaluate, false, "Mode flag: evaluates a solution.");

namespace akatsuki {

int CompileMain(const char* solution_path) {
  SolutionSpec solution_spec;
  CHECK(std::ifstream(solution_path) >> solution_spec) << "Malformed solution.";
  if (!ValidateSolution(solution_spec, true)) {
    std::cout << "Invalid solution.\n";
    exit(1);
  }
  ProblemSpec problem_spec = CompileProblem(solution_spec);
  CHECK(std::cout << problem_spec) << "Failed to write problem.";
  return 0;
}

int EvaluateMain(const char* problem_path, const char* solution_path) {
  ProblemSpec problem_spec;
  CHECK(std::ifstream(problem_path) >> problem_spec) << "Malformed problem.";
  SolutionSpec solution_spec;
  CHECK(std::ifstream(solution_path) >> solution_spec) << "Malformed solution.";
  if (!ValidateSolution(solution_spec, false)) {
    std::cout << "Invalid solution.\n";
    exit(1);
  }
  int resemblance_int = Evaluate(problem_spec, solution_spec);
  std::cout << "integer_resemblance: " << resemblance_int << std::endl;
  return 0;
}

void PrintUsage() {
  std::cerr << "Usage:" << std::endl;
  std::cerr << "  akatsuki --compile <solution>" << std::endl;
  std::cerr << "  akatsuki --evaluate <problem> <solution>" << std::endl;
}

int Main(int argc, char** argv) {
  int num_modes = int(FLAGS_compile) + int(FLAGS_evaluate);
  if (num_modes != 1) {
    PrintUsage();
    return 1;
  }

  if (FLAGS_compile) {
    if (argc != 2) {
      PrintUsage();
      return 1;
    }
    return CompileMain(argv[1]);
  } else if (FLAGS_evaluate) {
    if (argc != 3) {
      PrintUsage();
      return 1;
    }
    return EvaluateMain(argv[1], argv[2]);
  }
  LOG(FATAL) << "what?";
  return 1;
}

}  // namespace akatsuki

int main(int argc, char** argv) {
  google::InstallFailureSignalHandler();
  google::InitGoogleLogging(argv[0]);
  google::ParseCommandLineFlags(&argc, &argv, true);
  return akatsuki::Main(argc, argv);
}
