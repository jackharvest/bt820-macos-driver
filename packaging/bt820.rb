class Bt820 < Formula
  include Language::Python::Virtualenv

  desc "Driver for the REKDOM BT820 4x6 thermal label printer (Rongta RP4xx, TSPL)"
  homepage "https://github.com/jackharvest/bt820"
  url "https://github.com/jackharvest/bt820/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_AFTER_TAGGING"
  license "MIT"

  depends_on "libusb"
  depends_on "python@3.13"
  # Pillow builds from source; these are its image backends.
  depends_on "freetype"
  depends_on "jpeg-turbo"
  depends_on "libtiff"
  depends_on "little-cms2"
  depends_on "openjpeg"
  depends_on "webp"

  resource "pyusb" do
    url "https://files.pythonhosted.org/packages/00/6b/ce3727395e52b7b76dfcf0c665e37d223b680b9becc60710d4bc08b7b7cb/pyusb-1.3.1.tar.gz"
    sha256 "3af070b607467c1c164f49d5b0caabe8ac78dbed9298d703a8dbf9df4052d17e"
  end

  resource "pillow" do
    url "https://files.pythonhosted.org/packages/f3/0d/d0d6dea55cd152ce3d6767bb38a8fc10e33796ba4ba210cbab9354b6d238/pillow-11.3.0.tar.gz"
    sha256 "3828ee7586cd0b2091b6209e5ad53e20d0649bbe87164a459d0676e035e8f523"
  end

  # pypdfium2's sdist fetches a prebuilt pdfium during build, which the
  # Homebrew sandbox blocks -- use the per-arch wheels instead.
  on_arm do
    resource "pypdfium2" do
      url "https://files.pythonhosted.org/packages/08/99/1fe58428b69d2722dcbcfaa08ce71834a332c5b518fd58874bcef936b823/pypdfium2-5.13.0-py3-none-macosx_13_0_arm64.whl"
      sha256 "da5c7b74eebf40b5c1fbe1de01aa1edc8827a79fb1efd999616bc20dcaf77ba4"
    end
  end

  on_intel do
    resource "pypdfium2" do
      url "https://files.pythonhosted.org/packages/9f/41/06e26da88a4f5b4ed289325868717a186020661b7b221aa6df622711d31b/pypdfium2-5.13.0-py3-none-macosx_13_0_x86_64.whl"
      sha256 "2abedfb5c70992b19c780ed58d7f7b929e8ce8ee52c9140158f44317c90ec6c7"
    end
  end

  def install
    virtualenv_install_with_resources
    # bt820ctl finds its sibling binary and ../share/bt820.conf.
    bin.install "bin/bt820ctl", "bin/bt820-ippfilter"
    share.install "share/bt820.conf"
  end

  def caveats
    <<~EOS
      Command-line printing works now:
        bt820print label.pdf

      For a queue you can Cmd+P into (a local IPP Everywhere printer plus a
      CUPS queue named BT820, started at login):
        bt820ctl start

      To remove it again:
        bt820ctl uninstall
    EOS
  end

  test do
    assert_match "bt820", shell_output("#{bin}/bt820print --version")
  end
end
