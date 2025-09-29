{ pkgs, ... }: {
  channel = "stable-24.05";
  packages = [
    pkgs.openssh
    pkgs.gh
  ];
  idx.workspace = {
  };
}
