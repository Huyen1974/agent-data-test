{ pkgs, ... }: {
  channel = "stable-24.05";
  packages = [
    pkgs.openssh
    pkgs.gh
    pkgs.playwright-driver.browsers
    pkgs.nodejs_20
    pkgs.python311
    pkgs.terraform
    pkgs.pre-commit
  ];
  idx.workspace = {
    onCreate = {
      npm-install = "npm ci --prefix app-service-project";
      pre-commit-install = "pre-commit install";
      firebase-tools = "npm install -g firebase-tools";
    };
    onStart = {
      auth-check = "gh auth status || gh auth login --web";
    };
  };
}
