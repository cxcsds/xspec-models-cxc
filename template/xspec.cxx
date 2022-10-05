//  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021, 2022
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

// We require XSPEC 12.12.0 or later as the include directories have
// moved compared to XSPEC 12.11.1 and earlier.
//
#include <xsTypes.h>
#include <XSFunctions/Utilities/funcType.h>  // xsccCall and the like

#include <XSFunctions/Utilities/FunctionUtility.h>
#include <XSUtil/Utils/XSutility.h>

// This provides access to tabint, at least for XSPEC 12.12.1.
// It *does not* provide the necesssary symbol for XSPEC 12.12.0,
// unfortunately.
//
// Should we use XSFunctions/tableInterpolate.cxx instead - namely
//
// void tableInterpolate(const RealArray& energyArray,
//                       const RealArray& params,
//                       string fileName,
//                       int spectrumNumber,
//                       RealArray& fluxArray,
//                       RealArray& fluxErrArray,
//                       const string& initString,
//                       const string& tableType,
//                       const bool readFull);
//
#include <XSFunctions/Utilities/xsFortran.h>

// Where do we get the model definitions? At the moment we manually add
// the FORTRAN definition as I couldn't get functionMap to work.
//
#include <XSFunctions/functionMap.h>
#include <XSFunctions/funcWrappers.h>

// templates for binding the models
//
#include "xspec_models_cxc.hh"


// Allow access to the RealArray typedef.
//
PYBIND11_MAKE_OPAQUE(RealArray);

namespace py = pybind11;
using namespace pybind11::literals;

PYBIND11_MODULE(_compiled, m) {
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

Support routines
----------------
get_version - The version of the XSPEC model library.
chatter - Get or set the XSPEC chatter level.
abundance - Get or set the abundance-table setting.
cross_section - Get or set the cross-section-table setting.
elementAbundance - Return the abundance for an element by name or atomic number.
elementName - Get the name of an element given the atomic number.
cosmology - Get or set the cosmology (H0, q0, lambda0) settings.
clearXFLT, getNumberXFLT, getXFLT, inXFLT, setXFLT - XFLT keyword handlnig.
clearModelString, getModelString, setModelString - model string database.
clearDb, getDb, setDb - keyword database.

Table Models
------------
tableModel

Additive models
---------------
@@ADDMODELS@@

Multiplicative models
---------------------
@@MULMODELS@@

Convolution models
------------------
@@CONMODELS@@

)doc";

    // Access RealArray - unfortunately there's no
    // py::bind_valarray template in pybind/stl_bind.c
    //
    py::class_<RealArray>(m, "RealArray")

      .def(py::init([](const std::size_t n) {
	return RealArray(n);
      }), "Create an array of n zeros.")

      .def(py::init([](py::array_t<Real, py::array::c_style | py::array::forcecast> &values) {

	py::buffer_info buf = values.request();
	if (buf.ndim != 1)
	  throw pybind11::value_error("values must be 1D");

	double *ptr = static_cast<Real *>(buf.ptr);
	return RealArray(ptr, buf.size);
      }), "Copy the data into an array.")

      .def("__len__", &RealArray::size)
      .def("__iter__", [](RealArray &v) {
	return py::make_iterator(std::begin(v), std::end(v));
      }, py::keep_alive<0, 1>()) // Keep vector alive while iterator is used

      .def("__repr__", [](const RealArray &v) {
	std::ostringstream s;
	s << '[';
	for (std::size_t i=0; i < v.size(); ++i) {
	  s << v[i];
	  if (i != v.size() - 1)
	    s << ", ";
	}
	s << ']';
	return s.str();
      }, "Display the array contents.")

      // I tried to support slice access for get and set but this
      // lead to boomtown (segfault-a-plenty) so, as it's not really
      // needed. I didn't explore any further.
      //
      .def("__getitem__", [](const RealArray &v, int i) {
	const int s = static_cast<int>(v.size());
	if (i < 0)
	  i += s;
	if (i < 0 || i >= s)
	  throw py::index_error();
	return v[i];
      })

      .def("__setitem__", [](RealArray &v, int i, const Real &value) {
	const int s = static_cast<int>(v.size());
	if (i < 0)
	  i += s;
	if (i < 0 || i >= s)
	  throw py::index_error();
	v[i] = value;
      })

      ;

    // Access to the library functionality. The string returned
    // by this routine is created on-the-fly and so I think it's
    // okay for pybind11 to take ownership if it.
    //
    //
    m.def("get_version",
	  []() { xspec_models_cxc::init(); return XSutility::xs_version(); },
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
	  []() { xspec_models_cxc::init(); return FunctionUtility::xwriteChatter(); },
	  "Get the XSPEC chatter level.");

    m.def("chatter",
	  [](int i) { xspec_models_cxc::init(); FunctionUtility::xwriteChatter(i); },
	  "Set the XSPEC chatter level.",
	  "chatter"_a);

    // Abundances
    //
    m.def("abundance",
	  []() { xspec_models_cxc::init(); return FunctionUtility::ABUND(); },
	  "Get the abundance-table setting.",
	  py::return_value_policy::reference);

    m.def("abundance",
	  [](const string& value) { xspec_models_cxc::init(); return FunctionUtility::ABUND(value); },
	  "Set the abundance-table setting.",
	  "table"_a);

    // We check to see if an error was written to stderr to identify when the
    // input was invalid. This is not great!
    //
    m.def("elementAbundance",
	  [](const string& value) {
	    xspec_models_cxc::init();

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
	    xspec_models_cxc::init();
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
	  [](const size_t Z) { xspec_models_cxc::init(); return FunctionUtility::elements(Z - 1); },
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
	  []() { xspec_models_cxc::init(); return FunctionUtility::XSECT(); },
	  "Get the cross-section-table setting.",
	  py::return_value_policy::reference);

    m.def("cross_section",
	  [](const string& value) { xspec_models_cxc::init(); return FunctionUtility::XSECT(value); },
	  "Set the cross-section-table setting.",
	  "table"_a);

    // Cosmology settings: I can not be bothered exposing the per-setting values.
    //
    m.def("cosmology",
	  []() {
	    xspec_models_cxc::init();
	    std::map<std::string, float> answer;
	    answer["h0"] = FunctionUtility::getH0();
	    answer["q0"] = FunctionUtility::getq0();
	    answer["lambda0"] = FunctionUtility::getlambda0();
	    return answer;
	  },
	  "What is the current cosmology (H0, q0, lambda0).");

    m.def("cosmology",
	  [](float h0, float q0, float lambda0) {
	    xspec_models_cxc::init();
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
	  []() { xspec_models_cxc::init(); return FunctionUtility::clearXFLT(); },
	  "Clear the XFLT database for all spectra.");

    m.def("getNumberXFLT",
	  [](int ifl) { xspec_models_cxc::init(); return FunctionUtility::getNumberXFLT(ifl); },
	  "How many XFLT keywords are defined for the spectrum?",
	  "spectrum"_a=1);

    m.def("getXFLT",
	  [](int ifl) { xspec_models_cxc::init(); return FunctionUtility::getAllXFLT(ifl); },
	  "What are all the XFLT keywords for the spectrum?",
	  "spectrum"_a=1,
	  py::return_value_policy::reference);

    m.def("getXFLT",
	  [](int ifl, int i) { xspec_models_cxc::init(); return FunctionUtility::getXFLT(ifl, i); },
	  "Return the given XFLT key.",
	  "spectrum"_a, "key"_a);

    m.def("getXFLT",
	  [](int ifl, string skey) { xspec_models_cxc::init(); return FunctionUtility::getXFLT(ifl, skey); },
	  "Return the given XFLT name.",
	  "spectrum"_a, "name"_a);

    m.def("inXFLT",
	  [](int ifl, int i) { xspec_models_cxc::init(); return FunctionUtility::inXFLT(ifl, i); },
	  "Is the given XFLT key set?",
	  "spectrum"_a, "key"_a);

    m.def("inXFLT",
	  [](int ifl, string skey) { xspec_models_cxc::init(); return FunctionUtility::inXFLT(ifl, skey); },
	  "Is the given XFLT name set?.",
	  "spectrum"_a, "name"_a);

    m.def("setXFLT",
	  [](int ifl, const std::map<string, Real>& values) { xspec_models_cxc::init(); FunctionUtility::loadXFLT(ifl, values); },
	  "Set the XFLT keywords for a spectrum",
	  "spectrum"_a, "values"_a);

    // Model database - as with XFLT how much do we just leave to Python?
    //
    // What are the memory requirements?
    //
    m.def("clearModelString",
	  []() { xspec_models_cxc::init(); return FunctionUtility::eraseModelStringDataBase(); },
	  "Clear the model string database.");

    m.def("getModelString",
	  []() { xspec_models_cxc::init(); return FunctionUtility::modelStringDataBase(); },
	  "Get the model string database.",
	  py::return_value_policy::reference);

    m.def("getModelString",
	  [](const string& key) {
	    xspec_models_cxc::init();
	    auto answer = FunctionUtility::getModelString(key);
	    if (answer == FunctionUtility::NOT_A_KEY())
	      throw pybind11::key_error(key);
	    return answer;
	  },
	  "Get the key from the model string database.",
	  "key"_a);

    m.def("setModelString",
	  [](const string& key, const string& value) { xspec_models_cxc::init(); FunctionUtility::setModelString(key, value); },
	  "Get the key from the model string database.",
	  "key"_a, "value"_a);

    // "keyword" database values - similar to XFLT we could leave most of this to
    // Python.
    //
    m.def("clearDb",
	  []() { xspec_models_cxc::init(); return FunctionUtility::clearDb(); },
	  "Clear the keyword database.");

    m.def("getDb",
	  []() { xspec_models_cxc::init(); return FunctionUtility::getAllDbValues(); },
	  "Get the keyword database.",
	  py::return_value_policy::reference);

    // If the keyword is not an element then we get a string message and a set
    // return value. Catching this is annoying.
    //
    m.def("getDb",
	  [](const string keyword) {
	    xspec_models_cxc::init();

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
	  [](const string keyword, const double value) { xspec_models_cxc::init(); FunctionUtility::loadDbValue(keyword, value); },
	  "Set the keyword in the database to the given value.",
	  "keyword"_a, "value"_a);

    // Table-model support
    //
    m.def("tableModel",
	  [](const string filename, const string tableType,
	     py::array_t<float, py::array::c_style | py::array::forcecast> pars,
	     py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
	     const int spectrumNumber) {

	    py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
	    if (pbuf.ndim != 1 || ebuf.ndim != 1)
	      throw pybind11::value_error("pars and energyArray must be 1D");

	    if (ebuf.size < 3)
	      throw pybind11::value_error("Expected at least 3 bin edges");

	    // Should we force spectrumNumber >= 1?

	    const int nelem = ebuf.size - 1;

	    // Can we easily zero out the arrays?
	    auto result = py::array_t<float>(nelem);
	    auto errors = std::vector<float>(nelem);

	    py::buffer_info obuf = result.request();

	    float *pptr = static_cast<float *>(pbuf.ptr);
	    float *eptr = static_cast<float *>(ebuf.ptr);
	    float *optr = static_cast<float *>(obuf.ptr);

	    xspec_models_cxc::init();
	    tabint(eptr, nelem, pptr, pbuf.size,
		   filename.c_str(), spectrumNumber,
		   tableType.c_str(), optr, errors.data());
	    return result;
	  },
	  "XSPEC table model.",
	  "table"_a, "table_type"_a, "pars"_a, "energies"_a, "spectrum"_a=1);

    m.def("tableModel",
	  [](const string filename, const string tableType,
	     py::array_t<float, py::array::c_style | py::array::forcecast> pars,
	     py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
	     py::array_t<float, py::array::c_style | py::array::forcecast> output,
	     const int spectrumNumber) {

	    py::buffer_info pbuf = pars.request(),
	      ebuf = energyArray.request(),
	      obuf = output.request();
	    if (pbuf.ndim != 1 || ebuf.ndim != 1 || obuf.ndim != 1)
	      throw pybind11::value_error("pars, energyArray, and model must be 1D");

	    if (ebuf.size < 3)
	      throw pybind11::value_error("Expected at least 3 bin edges");

	    xspec_models_cxc::validate_grid_size(ebuf.size, obuf.size);

	    // Should we force spectrumNumber >= 1?

	    const int nelem = ebuf.size - 1;

	    // Can we easily zero out the arrays?
	    auto errors = std::vector<float>(nelem);

	    float *pptr = static_cast<float *>(pbuf.ptr);
	    float *eptr = static_cast<float *>(ebuf.ptr);
	    float *optr = static_cast<float *>(obuf.ptr);

	    xspec_models_cxc::init();
	    tabint(eptr, nelem, pptr, pbuf.size,
		   filename.c_str(), spectrumNumber,
		   tableType.c_str(), optr, errors.data());
	    return output;
	  },
	  "XSPEC table model; inplace.",
	  "table"_a, "table_type"_a, "pars"_a, "energies"_a, "model"_a, "spectrum"_a=1,
	  py::return_value_policy::reference);

    // Add the models, auto-generated from the model.dat file.
    //
@@MODELS@@

}
