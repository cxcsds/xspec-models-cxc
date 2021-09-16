//  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021
//  Smithsonian Astrophysical Observatory
//
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation; either version 3 of the License, or
//  (at your option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License along
//  with this program; if not, write to the Free Software Foundation, Inc.,
//  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
//

#include <iostream>
#include <fstream>

#include <pybind11/pybind11.h>
// #include <pybind11/stl.h>
#include <pybind11/numpy.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

// We require XSPEC 12.12.0 as the include directories have
// moved compared to XSPEC 12.11.1 and earlier.
//
#include <xsTypes.h>
#include <XSFunctions/Utilities/funcType.h>  // xsccCall and the like

#include <XSFunctions/Utilities/xsFortran.h>  // needed for FNINIT - anything else?
#include <XSFunctions/Utilities/FunctionUtility.h>
#include <XSUtil/Utils/XSutility.h>

// Where do we get the model definitions? At the moment we manually add
// the FORTRAN definition as I couldn't get functionMap to work.
//
#include <XSFunctions/functionMap.h>
#include <XSFunctions/funcWrappers.h>

namespace py = pybind11;
using namespace pybind11::literals;

// Initialize the XSPEC interface. We only want to do this once, and
// we want to be lazy - i.e. we don't want this done when the module
// is loaded (this is mainly a requirement from Sherpa and could be
// removed).
//
// Can we make this accessible to other users (e.g. for people who
// want to bind to user models?).
//
const void init() {
  static bool ran = false;
  if (ran) { return; }

  // A common problem case
  if (!getenv("HEADAS"))
    throw std::runtime_error("The HEADAS environment variable is not set!");

  // FNINIT is a bit chatty, so hide the stdout buffer for this call.
  // This is based on code from Sherpa.
  //
  std::streambuf* cout_sbuf = std::cout.rdbuf();
  std::ofstream fout("/dev/null");
  if (cout_sbuf != NULL && fout.is_open())
    std::cout.rdbuf(fout.rdbuf()); // temporary redirect stdout to /dev/null

  try {

    // Can this fail?
    FNINIT();

  } catch(...) {

    // Get back original std::cout
    std::cout.clear();
    std::cout.rdbuf(cout_sbuf);
    fout.clear();
    fout.close();

    throw std::runtime_error("Unable to initialize XSPEC model library");
  }

  // Get back original std::cout
  std::cout.clear();
  std::cout.rdbuf(cout_sbuf);
  fout.clear();
  fout.close();

  ran = true;
}


// The FORTRAN interface looks like
//
//   void agnsed_(float* ear, int* ne, float* param, int* ifl, float* photar, float* photer);
//
// The C_xxx interface looks like
//
//   void C_apec(const double* energy, int nFlux, const double* params,
//        int spectrumNumber, double* flux, double* fluxError,
//        const char* initStr);
//
// The CXX_xxx interface is
//
//   void CXX_apec(const RealArray& energyArray, const RealArray& params,
//        int spectrumNumber, RealArray& fluxArray, RealArray& fluxErrArray,
//        const string& initString);
//
// where RealArray is defined in xsTypes.h as
//
//   typedef double Real;
//   typedef std::valarray<Real> RealArray;
//
// but is it safe to assume this? We avoid this error by wrapping the C_xxx
// version.
//
template <xsccCall model, int NumPars>
py::array_t<Real> wrapper_C(py::array_t<Real> pars, py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  if (pbuf.size != NumPars) {
    std::ostringstream err;
    err << "Expected " << NumPars << " parameters but sent " << pbuf.size;
    throw std::runtime_error(err.str());
  }

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at leat 3 bin edges");

  const int nelem = ebuf.size - 1;
  const int ifl = 1;

  // Can we easily zero out the arrays?
  auto result = py::array_t<Real>(nelem);
  auto errors = std::vector<Real>(nelem);

  py::buffer_info obuf = result.request();

  double *pptr = static_cast<Real *>(pbuf.ptr);
  double *eptr = static_cast<Real *>(ebuf.ptr);
  double *optr = static_cast<Real *>(obuf.ptr);

  init();
  model(eptr, nelem, pptr, ifl, optr, errors.data(), "");
  return result;
}


template <xsf77Call model, int NumPars>
py::array_t<float> wrapper_f(py::array_t<float> pars, py::array_t<float, py::array::c_style | py::array::forcecast> energyArray) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  if (pbuf.size != NumPars) {
    std::ostringstream err;
    err << "Expected " << NumPars << " parameters but sent " << pbuf.size;
    throw std::runtime_error(err.str());
  }

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at leat 3 bin edges");

  const int nelem = ebuf.size - 1;
  const int ifl = 1;

  // Can we easily zero out the arrays?
  auto result = py::array_t<float>(nelem);
  auto errors = std::vector<float>(nelem);

  py::buffer_info obuf = result.request();

  float *pptr = static_cast<float *>(pbuf.ptr);
  float *eptr = static_cast<float *>(ebuf.ptr);
  float *optr = static_cast<float *>(obuf.ptr);

  init();
  model(eptr, nelem, pptr, ifl, optr, errors.data());
  return result;
}


PYBIND11_MODULE(xspec_models_cxc, m) {
#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif

    m.doc() = R"doc(
Call XSPEC models from Python
=============================

Highly experimental.

The XSPEC model library is automatically initialized on the first call
to one of the functions or models.

Additive models
---------------
@@ADDMODELS@@

Multiplicative models
---------------
@@MULMODELS@@

)doc";

    // Access to the library functionality. The string returned
    // by this routine is created on-the-fly and so I think it's
    // okay for pybind11 to take ownership if it.
    //
    //
    m.def("get_version",
	  []() { init(); return XSutility::xs_version(); },
	  "The version of the XSPEC model library");

    // You could be fancy and have an XSPEC object where these
    // are get/set attributes, but leave that to a separate
    // module (or a later attempt) since we could encode such
    // an object with pybind11.
    //
    // It is also not clear whether we need to manually create
    // these lambdas, but I was seeing issues when I just wanted
    // to bind to FunctionUtility::xwriteChatter, for instance,
    // which I didn't want to bother identifying.
    //

    m.def("chatter",
	  []() { init(); return FunctionUtility::xwriteChatter(); },
	  "Get the XSPEC chatter level.");

    m.def("chatter",
	  [](int i) { init(); FunctionUtility::xwriteChatter(i); },
	  "Set the XSPEC chatter level.",
	  "chatter"_a);

    m.def("abundance",
	  []() { init(); return FunctionUtility::ABUND(); },
	  "Get the abundance-table setting.",
	  py::return_value_policy::reference);

    m.def("abundance",
	  [](const string& value) { init(); return FunctionUtility::ABUND(value); },
	  "Set the abundance-table setting.",
	  "table"_a);

    m.def("elementAbundance",
	  [](const string& value) { init(); return FunctionUtility::getAbundance(value); },
	  "Return the abundance setting for an element given the name.",
	  "name"_a);

    m.def("elementAbundance",
	  [](const size_t Z) { init(); return FunctionUtility::getAbundance(Z); },
	  "Return the abundance setting for an element given the atomic number.",
	  "z"_a);

    m.def("elementName",
	  [](const size_t Z) { init(); return FunctionUtility::elements(Z - 1); },
	  "Return the name of an element given the atomic number.",
	  "z"_a,
	  py::return_value_policy::reference);

    // Add the models, auto-generated from the model.dat file.
    //
@@MODELS@@

}
