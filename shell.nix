{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    python38
    poetry
    docker
    docker-compose
  ];

  DOCKER_HOST = "unix:///tmp/podman.sock";

  shellHook = ''
    poetry env use python3.8
    poetry install
    if [ ! -S /tmp/podman.sock ]
    then
      echo Spawning podman process
      ${pkgs.podman}/bin/podman system service --time=0 $DOCKER_HOST &
    fi
  '';
}
