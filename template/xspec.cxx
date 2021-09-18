//  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021
//  Smithsonian Astrophysical Observatory
//
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <iostream>
#include <fstream>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
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
  std::ostringstream local;
  auto cout_buff = std::cout.rdbuf();
  std::cout.rdbuf(local.rdbuf());

  try {

    // Can this fail?
    FNINIT();

  } catch(...) {

    std::cout.rdbuf(cout_buff);
    throw std::runtime_error("Unable to initialize XSPEC model library\n" + local.str());
  }

  // Get back original std::cout
  std::cout.rdbuf(cout_buff);

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
py::array_t<Real> wrapper_C(py::array_t<Real> pars,
			    py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray,
			    const int spectrumNumber,
			    const string initStr) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  if (pbuf.size != NumPars) {
    std::ostringstream err;
    err << "Expected " << NumPars << " parameters but sent " << pbuf.size;
    throw std::runtime_error(err.str());
  }

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  // Should we force spectrumNumber >= 1?
  // We shouldn't be able to send in an invalid initStr so do not bother checking.

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto result = py::array_t<Real>(nelem);
  auto errors = std::vector<Real>(nelem);

  py::buffer_info obuf = result.request();

  double *pptr = static_cast<Real *>(pbuf.ptr);
  double *eptr = static_cast<Real *>(ebuf.ptr);
  double *optr = static_cast<Real *>(obuf.ptr);

  init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data(), initStr.c_str());
  return result;
}


template <xsf77Call model, int NumPars>
py::array_t<float> wrapper_f(py::array_t<float> pars,
			     py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
			     const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  if (pbuf.size != NumPars) {
    std::ostringstream err;
    err << "Expected " << NumPars << " parameters but sent " << pbuf.size;
    throw std::runtime_error(err.str());
  }

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto result = py::array_t<float>(nelem);
  auto errors = std::vector<float>(nelem);

  py::buffer_info obuf = result.request();

  float *pptr = static_cast<float *>(pbuf.ptr);
  float *eptr = static_cast<float *>(ebuf.ptr);
  float *optr = static_cast<float *>(obuf.ptr);

  init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data());
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

    // Abundances
    //
    m.def("abundance",
	  []() { init(); return FunctionUtility::ABUND(); },
	  "Get the abundance-table setting.",
	  py::return_value_policy::reference);

    m.def("abundance",
	  [](const string& value) { init(); return FunctionUtility::ABUND(value); },
	  "Set the abundance-table setting.",
	  "table"_a);

    // We check to see if an error was written to stderr to identify when the
    // input was invalid. This is not great!
    //
    m.def("elementAbundance",
	  [](const string& value) {
	    init();

	    std::ostringstream local;
	    auto cerr_buff = std::cerr.rdbuf();
	    std::cerr.rdbuf(local.rdbuf());

	    // Assume this can not throw an error
	    auto answer = FunctionUtility::getAbundance(value);

	    std::cerr.rdbuf(cerr_buff);
	    if (local.str() != "")
	      throw pybind11::key_error(value);

	    return answer;
	  },
	  "Return the abundance setting for an element given the name.",
	  "name"_a);

    m.def("elementAbundance",
	  [](const size_t Z) {
	    init();
	    if (Z < 1 || Z > FunctionUtility::NELEMS()) {
	      std::ostringstream emsg;
	      emsg << Z;
	      throw pybind11::index_error(emsg.str());
	    }

	    return FunctionUtility::getAbundance(Z);
	  },
	  "Return the abundance setting for an element given the atomic number.",
	  "z"_a);

    m.def("elementName",
	  [](const size_t Z) { init(); return FunctionUtility::elements(Z - 1); },
	  "Return the name of an element given the atomic number.",
	  "z"_a,
	  py::return_value_policy::reference);

    // Assume this is not going to change within a session!
    // Also we assume that this can be called without callnig FNINIT.
    //
    m.attr("numberElements") = FunctionUtility::NELEMS();

    // Cross sections
    //
    m.def("cross_section",
	  []() { init(); return FunctionUtility::XSECT(); },
	  "Get the cross-section-table setting.",
	  py::return_value_policy::reference);

    m.def("cross_section",
	  [](const string& value) { init(); return FunctionUtility::XSECT(value); },
	  "Set the cross-section-table setting.",
	  "table"_a);

    // Cosmology settings: I can not be bothered exposing the per-setting values.
    //
    m.def("cosmology",
	  []() {
	    init();
	    std::map<std::string, float> answer;
	    answer["H0"] = FunctionUtility::getH0();
	    answer["q0"] = FunctionUtility::getq0();
	    answer["lambda0"] = FunctionUtility::getlambda0();
	    return answer;
	  },
	  "What is the current cosmology (H0, q0, lambda0).");

    m.def("cosmology",
	  [](float h0, float q0, float lambda0) {
	    init();
	    FunctionUtility::setH0(h0);
	    FunctionUtility::setq0(q0);
	    FunctionUtility::setlambda0(lambda0);
	  },
	  "Set the current cosmology.",
	  "h0"_a, "q0"_a, "lambda0"_a);

    // XFLT keyword handling: the names are hardly instructive. We could
    // just have an overloaded XFLT method which either queries or sets
    // the values, and then leave the rest to the user to do in Python.
    //
    m.def("clearXFLT",
	  []() { init(); return FunctionUtility::clearXFLT(); },
	  "Clear the XFLT database for all spectra.");

    m.def("getNumberXFLT",
	  [](int ifl) { init(); return FunctionUtility::getNumberXFLT(ifl); },
	  "How many XFLT keywords are defined for the spectrum?",
	  "spectrum"_a=1);

    m.def("getXFLT",
	  [](int ifl) { init(); return FunctionUtility::getAllXFLT(ifl); },
	  "What are all the XFLT keywords for the spectrum?",
	  "spectrum"_a=1,
	  py::return_value_policy::reference);

    m.def("getXFLT",
	  [](int ifl, int i) { init(); return FunctionUtility::getXFLT(ifl, i); },
	  "Return the given XFLT key.",
	  "spectrum"_a, "key"_a);

    m.def("getXFLT",
	  [](int ifl, string skey) { init(); return FunctionUtility::getXFLT(ifl, skey); },
	  "Return the given XFLT name.",
	  "spectrum"_a, "name"_a);

    m.def("inXFLT",
	  [](int ifl, int i) { init(); return FunctionUtility::inXFLT(ifl, i); },
	  "Is the given XFLT key set?",
	  "spectrum"_a, "key"_a);

    m.def("inXFLT",
	  [](int ifl, string skey) { init(); return FunctionUtility::inXFLT(ifl, skey); },
	  "Is the given XFLT name set?.",
	  "spectrum"_a, "name"_a);

    m.def("setXFLT",
	  [](int ifl, const std::map<string, Real>& values) { init(); FunctionUtility::loadXFLT(ifl, values); },
	  "Set the XFLT keywords for a spectrum",
	  "spectrum"_a, "values"_a);

    // Model database - as with XFLT how much do we just leave to Python?
    //
    // What are the memory requirements?
    //
    m.def("clearModelString",
	  []() { init(); return FunctionUtility::eraseModelStringDataBase(); },
	  "Clear the model string database.");

    m.def("getModelString",
	  []() { init(); return FunctionUtility::modelStringDataBase(); },
	  "Get the model string database.",
	  py::return_value_policy::reference);

    m.def("getModelString",
	  [](const string& key) {
	    init();
	    auto answer = FunctionUtility::getModelString(key);
	    if (answer == FunctionUtility::NOT_A_KEY())
	      throw pybind11::key_error(key);
	    return answer;
	  },
	  "Get the key from the model string database.",
	  "key"_a);

    m.def("setModelString",
	  [](const string& key, const string& value) { init(); FunctionUtility::setModelString(key, value); },
	  "Get the key from the model string database.",
	  "key"_a, "value"_a);

    // "keyword" database values - similar to XFLT we could leave most of this to
    // Python.
    //
    m.def("clearDb",
	  []() { init(); return FunctionUtility::clearDb(); },
	  "Clear the keyword database.");

    m.def("getDb",
	  []() { init(); return FunctionUtility::getAllDbValues(); },
	  "Get the keyword database.",
	  py::return_value_policy::reference);

    // If the keyword is not an element then we get a string message and a set
    // return value. Catching this is annoying.
    //
    m.def("getDb",
	  [](const string keyword) {
	    init();

	    std::ostringstream local;
	    auto cerr_buff = std::cerr.rdbuf();
	    std::cerr.rdbuf(local.rdbuf());

	    // Assume this can not throw an error
	    auto answer = FunctionUtility::getDbValue(keyword);

	    std::cerr.rdbuf(cerr_buff);
	    if (answer == BADVAL)
	      throw pybind11::key_error(keyword);

	    return answer;
	  },
	  "Get the keyword value from the database.",
	  "keyword"_a);

    m.def("setDb",
	  [](const string keyword, const double value) { init(); FunctionUtility::loadDbValue(keyword, value); },
	  "Set the keyword in the database to the given value.",
	  "keyword"_a, "value"_a);

    // Add the models, auto-generated from the model.dat file.
    //
@@MODELS@@

}
