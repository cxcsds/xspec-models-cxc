/*
 * Returns the version string of XSPEC. It appears to need to be
 * linked to just XSUtil, and does not need the library to be
 * initialized.
 */

#include <iostream>

#include <XSUtil/Utils/XSutility.h>

int main(int argc, char **argv) {
  std::cout << XSutility::xs_version() << std::endl;
  return 0;
}
