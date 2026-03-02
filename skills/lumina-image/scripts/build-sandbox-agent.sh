#!/usr/bin/env bash

sandbox_build_agent_image() {
  if [[ -z "${MS_PATH:-}" ]]; then
    echo "MS_PATH environment variable is not set. Set it to the CopilotLumina root." >&2
    return 1
  fi

  local unique_id
  unique_id="$(date +%Y%m%d%H%M%S)"

  local docker_image_tag
  docker_image_tag="luminaacrdev.azurecr.io/lixiangliu/lumina-sandbox-agent:${unique_id}"

  local project_root
  project_root="${MS_PATH}/CopilotLumina/sources/dev/SandboxService"

  local docker_file
  docker_file="${project_root}/Docker/agent.Dockerfile"

  local docker_context
  docker_context="${project_root}"

  docker build --file "${docker_file}" --tag "${docker_image_tag}" "${docker_context}"
  if [[ $? -ne 0 ]]; then
    echo "Failed to build docker image: ${docker_image_tag}" >&2
    return 1
  fi

  docker push "${docker_image_tag}"
  if [[ $? -ne 0 ]]; then
    echo "Failed to push docker image: ${docker_image_tag}" >&2
    return 1
  fi

  echo "Docker image tag: ${docker_image_tag}"
}
