//  Copyright (C) 2009, 2015, 2017, 2020, 2021, 2022
//  Smithsonian Astrophysical Observatory
//
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef __xspec_models_cxc_hh__
#define __xspec_models_cxc_hh__

#include <iostream>
#include <fstream>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <XSFunctions/Utilities/xsFortran.h>  // needed for FNINIT - anything else?

namespace py = pybind11;
// using namespace pybind11::literals;

namespace xspec_models_cxc {

// Initialize the XSPEC interface. We only want to do this once, and
// we want to be lazy - i.e. we don't want this done when the module
// is loaded (this is mainly a requirement from Sherpa and could be
// removed).
//
// Can we make this accessible to other users (e.g. for people who
// want to bind to user models?).
//
void init() {
  static bool ran = false;
  if (ran) { return; }

  // A common problem case
  if (!getenv("HEADAS"))
    throw std::runtime_error("The HEADAS environment variable is not set!");

  // FNINIT is a bit chatty, so hide the stdout buffer for this call.
  // This is based on code from Sherpa but has been simplified.
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
// although xsf77Call seems to have the integer arguments passed
// directly rather than as a poniter.
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
// For the moment we just wrap the C_xxx interface rather than CXX_xxx.
//

// Check the number of parameters
void validate_par_size(const int NumPars, const int got) {
  if (NumPars == got)
    return;

  std::ostringstream err;
  err << "Expected " << NumPars << " parameters but sent " << got;
  throw std::runtime_error(err.str());
}

// Provide a useful error message if the sizes don't match
void validate_grid_size(const int energySize, const int modelSize) {

  if (energySize == modelSize + 1)
    return;

  std::ostringstream err;
  err << "Energy grid size must be 1 more than model: "
      << "energies has " << energySize << " elements and "
      << "model has " << modelSize << " elements";
  throw pybind11::value_error(err.str());
}


template <XSCCall model, int NumPars>
RealArray& wrapper_inplace_CXX(const RealArray pars,
			      const RealArray energyArray,
			      RealArray &output,
			      const int spectrumNumber,
			      const string initStr) {

  validate_par_size(NumPars, pars.size());

  if (energyArray.size() < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(energyArray.size(), output.size());

  // Should we force spectrumNumber >= 1?
  // We shouldn't be able to send in an invalid initStr so do not bother checking.

  auto errors = RealArray(output.size());

  xspec_models_cxc::init();
  model(energyArray, pars, spectrumNumber, output, errors, initStr.c_str());
  return output;
}


template <xsccCall model, int NumPars>
py::array_t<Real> wrapper_C(py::array_t<Real, py::array::c_style | py::array::forcecast> pars,
			    py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray,
			    const int spectrumNumber,
			    const string initStr) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  validate_par_size(NumPars, pbuf.size);

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

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data(), initStr.c_str());
  return result;
}


// I believe this shoud be marked py::return_value_policy::reference
//
template <xsccCall model, int NumPars>
py::array_t<Real> wrapper_inplace_C(py::array_t<Real, py::array::c_style | py::array::forcecast> pars,
				    py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray,
				    py::array_t<Real, py::array::c_style | py::array::forcecast> output,
				    const int spectrumNumber,
				    const string initStr) {

  py::buffer_info pbuf = pars.request(),
    ebuf = energyArray.request(),
    obuf = output.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1|| obuf.ndim != 1)
    throw pybind11::value_error("pars, energyArray, and model must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(ebuf.size, obuf.size);

  // Should we force spectrumNumber >= 1?
  // We shouldn't be able to send in an invalid initStr so do not bother checking.

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto errors = std::vector<Real>(nelem);

  double *pptr = static_cast<Real *>(pbuf.ptr);
  double *eptr = static_cast<Real *>(ebuf.ptr);
  double *optr = static_cast<Real *>(obuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data(), initStr.c_str());
  return output;
}


// If we had a template for fortranCall parametrized on the data type (float or double)
// then we could use that to avoid having repeated call. In fact, you almost-certainly
// can do this, but
//
// a) my template-foo is not strong enough
// b) it may depend on the C++ version we are using
//
template <xsf77Call model, int NumPars>
py::array_t<float> wrapper_f(py::array_t<float, py::array::c_style | py::array::forcecast> pars,
			     py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
			     const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  validate_par_size(NumPars, pbuf.size);

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

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data());
  return result;
}


// I believe this shoud be marked py::return_value_policy::reference
//
template <xsf77Call model, int NumPars>
py::array_t<float> wrapper_inplace_f(py::array_t<float, py::array::c_style | py::array::forcecast> pars,
				     py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
				     py::array_t<float, py::array::c_style | py::array::forcecast> output,
				     const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(),
    ebuf = energyArray.request(),
    obuf = output.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1|| obuf.ndim != 1)
    throw pybind11::value_error("pars, energyArray, and model must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(ebuf.size, obuf.size);

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto errors = std::vector<float>(nelem);

  float *pptr = static_cast<float *>(pbuf.ptr);
  float *eptr = static_cast<float *>(ebuf.ptr);
  float *optr = static_cast<float *>(obuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data());
  return output;
}


// Can we parametrize the f77 wrappers to automatically pick up
// the difference between xsf77Call and xsF77Call?
//  
template <xsF77Call model, int NumPars>
py::array_t<double> wrapper_F(py::array_t<double, py::array::c_style | py::array::forcecast> pars,
			      py::array_t<double, py::array::c_style | py::array::forcecast> energyArray,
			      const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(), ebuf = energyArray.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto result = py::array_t<double>(nelem);
  auto errors = std::vector<double>(nelem);

  py::buffer_info obuf = result.request();

  double *pptr = static_cast<double *>(pbuf.ptr);
  double *eptr = static_cast<double *>(ebuf.ptr);
  double *optr = static_cast<double *>(obuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data());
  return result;
}


// I believe this shoud be marked py::return_value_policy::reference
//
template <xsF77Call model, int NumPars>
py::array_t<double> wrapper_inplace_F(py::array_t<double, py::array::c_style | py::array::forcecast> pars,
				      py::array_t<double, py::array::c_style | py::array::forcecast> energyArray,
				      py::array_t<double, py::array::c_style | py::array::forcecast> output,
				      const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(),
    ebuf = energyArray.request(),
    obuf = output.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1|| obuf.ndim != 1)
    throw pybind11::value_error("pars, energyArray, and model must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(ebuf.size, obuf.size);

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto errors = std::vector<double>(nelem);

  double *pptr = static_cast<double *>(pbuf.ptr);
  double *eptr = static_cast<double *>(ebuf.ptr);
  double *optr = static_cast<double *>(obuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, optr, errors.data());
  return output;
}


// I believe this shoud be marked py::return_value_policy::reference
//
template <xsccCall model, int NumPars>
py::array_t<Real> wrapper_con_C(py::array_t<Real, py::array::c_style | py::array::forcecast> pars,
				py::array_t<Real, py::array::c_style | py::array::forcecast> energyArray,
				py::array_t<Real, py::array::c_style | py::array::forcecast> inModel,
				const int spectrumNumber,
				const string initStr) {

  py::buffer_info pbuf = pars.request(),
    ebuf = energyArray.request(),
    mbuf = inModel.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1 || mbuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(ebuf.size, mbuf.size);

  // Should we force spectrumNumber >= 1?
  // We shouldn't be able to send in an invalid initStr so do not bother checking.

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto errors = std::vector<Real>(nelem);

  double *pptr = static_cast<Real *>(pbuf.ptr);
  double *eptr = static_cast<Real *>(ebuf.ptr);
  double *mptr = static_cast<Real *>(mbuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, mptr, errors.data(), initStr.c_str());
  return inModel;
}


// I believe this shoud be marked py::return_value_policy::reference
//
template <xsf77Call model, int NumPars>
py::array_t<float> wrapper_con_f(py::array_t<float, py::array::c_style | py::array::forcecast> pars,
				 py::array_t<float, py::array::c_style | py::array::forcecast> energyArray,
				 py::array_t<float, py::array::c_style | py::array::forcecast> inModel,
				 const int spectrumNumber) {

  py::buffer_info pbuf = pars.request(),
    ebuf = energyArray.request(),
    mbuf = inModel.request();
  if (pbuf.ndim != 1 || ebuf.ndim != 1 || mbuf.ndim != 1)
    throw pybind11::value_error("pars and energyArray must be 1D");

  validate_par_size(NumPars, pbuf.size);

  if (ebuf.size < 3)
    throw pybind11::value_error("Expected at least 3 bin edges");

  validate_grid_size(ebuf.size, mbuf.size);

  // Should we force spectrumNumber >= 1?
  // We shouldn't be able to send in an invalid initStr so do not bother checking.

  const int nelem = ebuf.size - 1;

  // Can we easily zero out the arrays?
  auto errors = std::vector<float>(nelem);

  float *pptr = static_cast<float *>(pbuf.ptr);
  float *eptr = static_cast<float *>(ebuf.ptr);
  float *mptr = static_cast<float *>(mbuf.ptr);

  xspec_models_cxc::init();
  model(eptr, nelem, pptr, spectrumNumber, mptr, errors.data());
  return inModel;
}

} // namespace: xspec_models_cxc

#endif
