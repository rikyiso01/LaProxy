{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    python38
    python310
    poetry
    docker
    docker-compose
  ];

  shellHook = ''
    if [ -z $DOCS ]
    then
      poetry env use python3.8
    else
      poetry env use python3.10
    fi
    poetry install
    if [ -z $DOCKER_HOST ]
    then
      echo 'Missing DOCKER_HOST environment variable'
      export DOCKER_HOST='unix:///tmp/podman.sock'
      if [ ! -S /tmp/podman.sock ]
      then
        echo 'Spawning podman process'
        ${pkgs.podman}/bin/podman system service --time=0 $DOCKER_HOST &
      fi
    fi
  '';
}
