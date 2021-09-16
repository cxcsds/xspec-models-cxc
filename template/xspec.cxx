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

#include <pybind11/pybind11.h>
// #include <pybind11/stl.h>
#include <pybind11/numpy.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

// We require XSPEC 12.12.0 as the include directories have
// moved compared to XSPEC 12.11.1 and earlier.
//
#include <xsTypes.h>

#include <XSFunctions/Utilities/xsFortran.h>  // needed for FNINIT - anything else?
#include <XSFunctions/Utilities/FunctionUtility.h>
#include <XSUtil/Utils/XSutility.h>

// C_<model> are declared here; the other models are defined in
// functionMap.h but that requires using the XSPEC build location
// rather than install location.
//
#include <XSFunctions/funcWrappers.h>


namespace py = pybind11;

// The C_xxx interface looks like
//
//   void C_apec(const double* energy, int nFlux, const double* params,
//        int spectrumNumber, double* flux, double* fluxError,
//        const char* initStr);
//
// and the CXX_xxx interface is
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
template <void (*model)(const double* energy, int nFlux, const double* params,
			int spectrumNumber, double* flux, double* fluxError,
			const char* initStr),
	  int NumPars>
py::array_t<Real> wrapper(py::array_t<Real> pars, py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw std::runtime_error("pars and energyArray must be 1D");

  if (pbuf.size != NumPars) {
    std::ostringstream err;
    err << "Expected " << NumPars << " parameters but sent " << pbuf.size;
    throw std::runtime_error(err.str());
  }

  if (ebuf.size < 3)
    throw std::runtime_error("Expected at leat 3 bin edges");

  auto result = py::array_t<Real>(ebuf.size - 1);

  py::buffer_info obuf = result.request();

  double *pptr = static_cast<Real *>(pbuf.ptr);
  double *eptr = static_cast<Real *>(ebuf.ptr);
  double *optr = static_cast<Real *>(obuf.ptr);

  model(eptr, ebuf.size - 1, pptr, 1, optr, NULL, "");
  return result;
}


PYBIND11_MODULE(xspec_models_cxc, m) {
#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif

    m.doc() = R"pbdoc(
        Call XSPEC models from Python
        -----------------------------

        Highly experimental.
    )pbdoc";

    // Can we make this lazily initalized?
    //
    m.def("init", &FNINIT, "Initialize the XSPEC model library.");

    // Access to the library functionality. The string returned
    // by this routine is created on-the-fly and so I think it's
    // okay for pybind11 to take ownership if it.
    //
    //
    m.def("get_version", &XSutility::xs_version,
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
	  []() { return FunctionUtility::xwriteChatter(); },
	  "Get the XSPEC chatter level.");

    m.def("chatter",
	  [](int i) { FunctionUtility::xwriteChatter(i); },
	  "Set the XSPEC chatter level.");

    m.def("abundance",
	  []() { return FunctionUtility::ABUND(); },
	  "Get the abundance-table setting.",
	  py::return_value_policy::reference);

    m.def("abundance",
	  [](const string& value) { return FunctionUtility::ABUND(value); },
	  "Set the abundance-table setting.");

    m.def("elementAbundance",
	  [](const string& value) { return FunctionUtility::getAbundance(value); },
	  "Return the abundance setting for an element (name).");

    m.def("elementAbundance",
	  [](const size_t Z) { return FunctionUtility::getAbundance(Z); },
	  "Return the abundance setting for an element (atomic number).");

    m.def("elementName",
	  [](const size_t Z) { return FunctionUtility::elements(Z - 1); },
	  "Return the name of an element (atomic number).",
	  py::return_value_policy::reference);

    // Add the models, auto-generated from the model.dat file.
    //
@@MODELS@@

}
