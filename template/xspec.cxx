//  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021, 2022, 2023, 2026
//  Smithsonian Astrophysical Observatory
//
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <iostream>
#include <fstream>
#include <map>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/map.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

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

namespace nb = nanobind;
using namespace nb::literals;

NB_MODULE(_compiled, m) {
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

Models are normally evaluated for a single set of parameters, by
sending in pars as a 1D array. To evaluate the model for multiple
parameter sets at once, send in pars as a 2D array with one row per
parameter set (shape (nset, npars)): the model is then evaluated for
each row and, for the non-inplace routines, the return value has shape
(nset, nbin), where nbin is the number of energy bins (the energies
grid still has nbin + 1 elements). For the inplace and convolution
routines the out/model argument must have shape (nset, nbin) in this
case, and each row is changed in place.

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

    // Access RealArray - the C++-style interface (the <name>_ models)
    // uses this type. Note that the interface only supports 1D
    // arrays, so it can not be used with multiple parameter sets.
    //
    nb::class_<RealArray>(m, "RealArray")

      .def(nb::init<size_t>(),
	   "Create an array of n zeros.")

      .def(nb::init<const RealArray &>(),
	   "Create a copy of an existing array.")

      .def("__init__",
	   [](RealArray *v, nb::sequence values) {

	     // Convert the sequence - a list, tuple, or numpy array -
	     // to an array of Real values. A numpy array could be
	     // copied directly but this also supports mixed inputs.
	     //
	     Py_ssize_t n = PySequence_Size(values.ptr());
	     if (n < 0)
	       throw nb::type_error("values must be a sequence");

	     std::vector<Real> vals;
	     vals.reserve(n);
	     for (Py_ssize_t i = 0; i < n; ++i) {
	       nb::object item = nb::steal(PySequence_GetItem(values.ptr(), i));
	       double value = PyFloat_AsDouble(item.ptr());
	       if (value == -1.0 && PyErr_Occurred())
		 throw nb::type_error("values must be numeric");

	       vals.push_back(static_cast<Real>(value));
	     }

	     new (v) RealArray(vals.data(), vals.size());
	   },
	   "Copy the data into an array.")

      .def("__len__", &RealArray::size)
      // Iteration is supported via __getitem__ (the Python sequence
      // protocol), which also keeps a reference to the array while it
      // is being iterated over.

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
      .def("__getitem__", [](const RealArray &v, Py_ssize_t i) {
	const Py_ssize_t s = static_cast<Py_ssize_t>(v.size());
	if (i < 0)
	  i += s;
	if (i < 0 || i >= s)
	  throw nb::index_error();
	return v[i];
      })

      .def("__setitem__", [](RealArray &v, Py_ssize_t i, const Real &value) {
	const Py_ssize_t s = static_cast<Py_ssize_t>(v.size());
	if (i < 0)
	  i += s;
	if (i < 0 || i >= s)
	  throw nb::index_error();
	v[i] = value;
      })

      ;

    // Access to the library functionality. The string returned
    // by this routine is created on-the-fly and so I think it's
    // okay for nanobind to take ownership if it.
    //
    //
    m.def("get_version",
	  []() { xspec_models_cxc::init(); return XSutility::xs_version(); },
	  "The version of the XSPEC model library");

    // You could be fancy and have an XSPEC object where these
    // are get/set attributes, but leave that to a separate
    // module (or a later attempt) since we could encode such
    // an object with nanobind.
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
	  "Get the abundance-table setting.");

    m.def("abundance",
	  [](const std::string& value) { xspec_models_cxc::init(); return FunctionUtility::ABUND(value); },
	  "Set the abundance-table setting.",
	  "table"_a);

    // We check to see if an error was written to stderr to identify when the
    // input was invalid. This is not great!
    //
    m.def("elementAbundance",
	  [](const std::string& value) {
	    xspec_models_cxc::init();

	    std::ostringstream local;
	    auto cerr_buff = std::cerr.rdbuf();
	    std::cerr.rdbuf(local.rdbuf());

	    // Assume this can not throw an error
	    auto answer = FunctionUtility::getAbundance(value);

	    std::cerr.rdbuf(cerr_buff);
	    if (local.str() != "")
	      throw nb::key_error(value.c_str());

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
	      throw nb::index_error(emsg.str().c_str());
	    }

	    return FunctionUtility::getAbundance(Z);
	  },
	  "Return the abundance setting for an element given the atomic number.",
	  "z"_a);

    m.def("elementName",
	  [](const size_t Z) { xspec_models_cxc::init(); return FunctionUtility::elements(Z - 1); },
	  "Return the name of an element given the atomic number.",
	  "z"_a);

    // Assume this is not going to change within a session!
    // Also we assume that this can be called without calling FNINIT.
    //
    m.attr("numberElements") = FunctionUtility::NELEMS();

    // Cross sections
    //
    m.def("cross_section",
	  []() { xspec_models_cxc::init(); return FunctionUtility::XSECT(); },
	  "Get the cross-section-table setting.");

    m.def("cross_section",
	  [](const std::string& value) { xspec_models_cxc::init(); return FunctionUtility::XSECT(value); },
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
	  "spectrum"_a=1);

    m.def("getXFLT",
	  [](int ifl, int i) { xspec_models_cxc::init(); return FunctionUtility::getXFLT(ifl, i); },
	  "Return the given XFLT key.",
	  "spectrum"_a, "key"_a);

    m.def("getXFLT",
	  [](int ifl, std::string skey) { xspec_models_cxc::init(); return FunctionUtility::getXFLT(ifl, skey); },
	  "Return the given XFLT name.",
	  "spectrum"_a, "name"_a);

    m.def("inXFLT",
	  [](int ifl, int i) { xspec_models_cxc::init(); return FunctionUtility::inXFLT(ifl, i); },
	  "Is the given XFLT key set?",
	  "spectrum"_a, "key"_a);

    m.def("inXFLT",
	  [](int ifl, std::string skey) { xspec_models_cxc::init(); return FunctionUtility::inXFLT(ifl, skey); },
	  "Is the given XFLT name set?.",
	  "spectrum"_a, "name"_a);

    m.def("setXFLT",
	  [](int ifl, const std::map<std::string, Real>& values) { xspec_models_cxc::init(); FunctionUtility::loadXFLT(ifl, values); },
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
	  "Get the model string database.");

    m.def("getModelString",
	  [](const std::string& key) {
	    xspec_models_cxc::init();
	    auto answer = FunctionUtility::getModelString(key);
	    if (answer == FunctionUtility::NOT_A_KEY())
	      throw nb::key_error(key.c_str());
	    return answer;
	  },
	  "Get the key from the model string database.",
	  "key"_a);

    m.def("setModelString",
	  [](const std::string& key, const std::string& value) { xspec_models_cxc::init(); FunctionUtility::setModelString(key, value); },
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
	  "Get the keyword database.");

    // If the keyword is not an element then we get a string message and a set
    // return value. Catching this is annoying.
    //
    m.def("getDb",
	  [](const std::string keyword) {
	    xspec_models_cxc::init();

	    std::ostringstream local;
	    auto cerr_buff = std::cerr.rdbuf();
	    std::cerr.rdbuf(local.rdbuf());

	    // Assume this can not throw an error
	    auto answer = FunctionUtility::getDbValue(keyword);

	    std::cerr.rdbuf(cerr_buff);
	    if (answer == BADVAL)
	      throw nb::key_error(keyword.c_str());

	    return answer;
	  },
	  "Get the keyword value from the database.",
	  "keyword"_a);

    m.def("setDb",
	  [](const std::string keyword, const double value) { xspec_models_cxc::init(); FunctionUtility::loadDbValue(keyword, value); },
	  "Set the keyword in the database to the given value.",
	  "keyword"_a, "value"_a);

    // Table-model support. The pars argument can be 1D (a single
    // parameter set) or 2D (shape (nset, npars)), in which case the
    // table is interpolated for each parameter set: the result - or
    // the model argument, for the inplace version - has shape (nset,
    // nelem) in this case.
    //
    m.def("tableModel",
	  [](const std::string filename, const std::string tableType,
	     const xspec_models_cxc::in_array<float> pars,
	     const xspec_models_cxc::in_array<float> energyArray,
	     const int spectrumNumber) {

	    if (energyArray.shape.size() != 1)
	      throw nb::value_error("energies must be 1D");

	    const int ngrid = static_cast<int>(energyArray.shape[0]);
	    if (ngrid < 3)
	      throw nb::value_error("Expected at least 3 bin edges");

	    const int nelem = ngrid - 1;

	    xspec_models_cxc::init();

	    if (pars.shape.size() == 1) {
	      // Should we force spectrumNumber >= 1?
	      auto result = xspec_models_cxc::make_result<float>({ nelem });
	      auto errors = std::vector<float>(nelem);
	      tabint(energyArray.data, nelem, pars.data,
		     static_cast<int>(pars.shape[0]),
		     filename.c_str(), spectrumNumber,
		     tableType.c_str(),
		     static_cast<float *>(result.data()), errors.data());
	      return result;
	    }

	    const int nset = static_cast<int>(pars.shape[0]);
	    const int npars = static_cast<int>(pars.shape[1]);
	    auto result = xspec_models_cxc::make_result<float>({ nset, nelem });
	    auto errors = std::vector<float>(nelem);
	    float *rdata = static_cast<float *>(result.data());
	    for (int i = 0; i < nset; ++i)
	      tabint(energyArray.data, nelem, pars.data + i * npars, npars,
		     filename.c_str(), spectrumNumber,
		     tableType.c_str(), rdata + i * nelem, errors.data());

	    return result;
	  },
	  "XSPEC table model.",
	  "table"_a, "table_type"_a, "pars"_a, "energies"_a, "spectrum"_a=1);

    m.def("tableModel",
	  [](const std::string filename, const std::string tableType,
	     const xspec_models_cxc::in_array<float> pars,
	     const xspec_models_cxc::in_array<float> energyArray,
	     xspec_models_cxc::out_array<float> output,
	     const int spectrumNumber) {

	    if (energyArray.shape.size() != 1)
	      throw nb::value_error("energies must be 1D");

	    const int ngrid = static_cast<int>(energyArray.shape[0]);
	    if (ngrid < 3)
	      throw nb::value_error("Expected at least 3 bin edges");

	    const int nelem = ngrid - 1;

	    if (output.shape.size() != pars.shape.size())
	      throw nb::value_error("model must have the same number of dimensions as pars");

	    xspec_models_cxc::init();

	    if (pars.shape.size() == 1) {
	      // Should we force spectrumNumber >= 1?
	      xspec_models_cxc::validate_grid_size(ngrid, static_cast<int>(output.shape[0]));
	      auto errors = std::vector<float>(nelem);
	      tabint(energyArray.data, nelem, pars.data,
		     static_cast<int>(pars.shape[0]),
		     filename.c_str(), spectrumNumber,
		     tableType.c_str(), output.data, errors.data());
	      return output.owner;
	    }

	    const int nset = static_cast<int>(pars.shape[0]);
	    const int npars = static_cast<int>(pars.shape[1]);
	    if (output.shape[0] != nset || output.shape[1] != nelem) {
	      std::ostringstream emsg;
	      emsg << "Expected model shape (" << nset << ", " << nelem
		   << ") but sent (" << output.shape[0] << ", "
		   << output.shape[1] << ")";
	      throw nb::value_error(emsg.str().c_str());
	    }

	    auto errors = std::vector<float>(nelem);
	    for (int i = 0; i < nset; ++i)
	      tabint(energyArray.data, nelem, pars.data + i * npars, npars,
		     filename.c_str(), spectrumNumber,
		     tableType.c_str(), output.data + i * nelem,
		     errors.data());

	    return output.owner;
	  },
	  "XSPEC table model; inplace.",
	  "table"_a, "table_type"_a, "pars"_a, "energies"_a, "model"_a, "spectrum"_a=1,
	  py::return_value_policy::reference);

    // Add the models, auto-generated from the model.dat file.
    //
@@MODELS@@

}
