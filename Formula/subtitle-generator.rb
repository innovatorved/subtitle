class SubtitleGenerator < Formula
  include Language::Python::Virtualenv

  desc "Industry-standard AI subtitle generation, styling, QC, and embedding toolkit"
  homepage "https://subtitle.vedgupta.in"
  url "https://files.pythonhosted.org/packages/source/s/subtitle-generator/subtitle_generator-4.0.0.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256_ON_RELEASE"
  license "MIT"

  depends_on "ffmpeg"
  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      Run the one-time binary installer to download the prebuilt whisper-cli:
        subtitle setup-whisper
      Then verify your environment with:
        subtitle doctor
    EOS
  end

  test do
    assert_match "4.0.0", shell_output("#{bin}/subtitle --version")
  end
end
