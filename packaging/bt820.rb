class Bt820 < Formula
  include Language::Python::Virtualenv

  desc "Driver for the REKDOM BT820 4x6 thermal label printer (Rongta RP4xx, TSPL)"
  homepage "https://github.com/jackharvest/bt820"
  url "https://github.com/jackharvest/bt820/archive/refs/tags/v1.0.4.tar.gz"
  sha256 "17002bd8079f152c86d1513660bf5700bbce843c131c428c1890d8d65b4bfc87"
  license "MIT"

  # freetype through webp are Pillow's image backends; it builds from source.
  depends_on "freetype"
  depends_on "jpeg-turbo"
  depends_on "libtiff"
  depends_on "libusb"
  depends_on "little-cms2"
  depends_on "openjpeg"
  depends_on "python@3.13"
  depends_on "webp"

  resource "pillow" do
    url "https://files.pythonhosted.org/packages/f3/0d/d0d6dea55cd152ce3d6767bb38a8fc10e33796ba4ba210cbab9354b6d238/pillow-11.3.0.tar.gz"
    sha256 "3828ee7586cd0b2091b6209e5ad53e20d0649bbe87164a459d0676e035e8f523"
  end

  # pypdfium2's sdist fetches a prebuilt pdfium during build, which the
  # Homebrew sandbox blocks -- use the per-arch wheels instead.
  resource "pypdfium2" do
    on_arm do
      url "https://files.pythonhosted.org/packages/08/99/1fe58428b69d2722dcbcfaa08ce71834a332c5b518fd58874bcef936b823/pypdfium2-5.13.0-py3-none-macosx_13_0_arm64.whl", using: :nounzip
      sha256 "da5c7b74eebf40b5c1fbe1de01aa1edc8827a79fb1efd999616bc20dcaf77ba4"
    end

    on_intel do
      url "https://files.pythonhosted.org/packages/9f/41/06e26da88a4f5b4ed289325868717a186020661b7b221aa6df622711d31b/pypdfium2-5.13.0-py3-none-macosx_13_0_x86_64.whl", using: :nounzip
      sha256 "2abedfb5c70992b19c780ed58d7f7b929e8ce8ee52c9140158f44317c90ec6c7"
    end
  end

  resource "pyusb" do
    url "https://files.pythonhosted.org/packages/00/6b/ce3727395e52b7b76dfcf0c665e37d223b680b9becc60710d4bc08b7b7cb/pyusb-1.3.1.tar.gz"
    sha256 "3af070b607467c1c164f49d5b0caabe8ac78dbed9298d703a8dbf9df4052d17e"
  end

  def install
    # jpeg-turbo is keg-only, so Pillow cannot find its headers on its own.
    # Point the compiler at every image backend explicitly.
    backends = %w[freetype jpeg-turbo libtiff little-cms2 openjpeg webp]
    ENV.append "CPPFLAGS", backends.map { |f| "-I#{formula_opt_include(f)}" }.join(" ")
    ENV.append "LDFLAGS", backends.map { |f| "-L#{formula_opt_lib(f)}" }.join(" ")

    venv = virtualenv_create(libexec, "python3.13")
    venv.pip_install resources.reject { |r| r.name == "pypdfium2" }
    # A wheel has to be handed to pip as a file, not staged as a source tree.
    resource("pypdfium2").stage do
      venv.pip_install Dir["*.whl"].first
    end
    venv.pip_install_and_link buildpath

    # bt820ctl finds its sibling binary and ../share/bt820.conf.
    bin.install "bin/bt820ctl", "bin/bt820-ippfilter"
    share.install "share/bt820.conf"
  end

  def caveats
    <<~EOS
      Print a label:
        bt820print label.pdf

      Add BT820 to the macOS print dialog (Cmd+P), started at login:
        bt820ctl start

      Remove it again:
        bt820ctl uninstall
    EOS
  end

  test do
    assert_match "bt820", shell_output("#{bin}/bt820print --version")
  end
end
