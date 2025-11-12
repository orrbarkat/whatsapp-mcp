create_cloudbuild_trigger() {
    # Early return if SKIP_TRIGGER is set
    if [[ "${SKIP_TRIGGER}" == "true" ]]; then
        log_info "Skipping Cloud Build trigger creation (--skip-trigger flag set)"
        return 0
    fi

    log_info "Configuring Cloud Build trigger..."

    # Validate that Artifact Registry exists before creating triggers
    validate_artifact_registry

    local trigger_name="whatsapp-mcp-main-trigger"

    # Check if trigger already exists (with consistent region usage)
    if gcloud builds triggers describe "${trigger_name}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" &>/dev/null; then
        log_warning "Trigger already exists: ${trigger_name}"
        log_info "Updating existing trigger..."

        # Delete and recreate to ensure correct configuration (with consistent region usage)
        gcloud builds triggers delete "${trigger_name}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --quiet
        log_info "Deleted existing trigger"
    fi

    # Detect repository type
    log_info "Detecting repository connection type..."

    # Check for GitHub connection
    local github_connections
    github_connections=$(gcloud builds connections list --region="${REGION}" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || echo "")

    if [[ -n "${github_connections}" ]]; then
        # Handle GitHub connections
        local connections_array=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && connections_array+=("$line")
        done <<< "${github_connections}"

        local connection_name=""
        local num_connections=${#connections_array[@]}

        if [[ ${num_connections} -eq 0 ]]; then
            # This shouldn't happen due to the outer check, but handle it anyway
            log_error "No GitHub App connections found."
            log_error ""
            log_error "A GitHub App connection is required to create triggers for GitHub-hosted repositories."
            log_error "To fix this issue, choose one of the following options:"
            log_error ""
            log_error "  1. Create a GitHub App connection in the Cloud Build console:"
            log_error "     https://console.cloud.google.com/cloud-build/connections"
            log_error ""
            log_error "  2. Use Cloud Source Repositories instead (requires creating a CSR repo):"
            log_error "     gcloud source repos create whatsapp-mcp"
            log_error ""
            log_error "  3. Skip trigger creation for now and set up manually later:"
            log_error "     ${SCRIPT_NAME} --skip-trigger"
            exit 1
        elif [[ ${num_connections} -eq 1 ]]; then
            connection_name="${connections_array[0]}"
            log_info "Found one GitHub connection: ${connection_name}"
        else
            log_info "Found ${num_connections} GitHub connections:"
            for i in "${!connections_array[@]}"; do
                echo "  $((i+1)). ${connections_array[i]}"
            done
            echo ""
            read -rp "Select connection number (1-${num_connections}): " selection

            if [[ ! "${selection}" =~ ^[0-9]+$ ]] || [[ ${selection} -lt 1 ]] || [[ ${selection} -gt ${num_connections} ]]; then
                log_error "Invalid selection. Exiting."
                exit 1
            fi

            connection_name="${connections_array[$((selection-1))]}"
            log_info "Selected connection: ${connection_name}"
        fi

        # Get the list of repositories for this connection
        local repositories
        repositories=$(gcloud builds repositories list --connection="${connection_name}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || echo "")

        if [[ -z "${repositories}" ]]; then
            log_error "No repositories found for connection '${connection_name}'"
            log_error ""
            log_error "Please connect a repository to this GitHub App connection:"
            log_error "  https://console.cloud.google.com/cloud-build/repositories"
            log_error ""
            log_error "Or skip trigger creation for now:"
            log_error "  ${SCRIPT_NAME} --skip-trigger"
            exit 1
        fi

        local repositories_array=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && repositories_array+=("$line")
        done <<< "${repositories}"

        local repo_name=""
        local num_repos=${#repositories_array[@]}

        if [[ ${num_repos} -eq 1 ]]; then
            repo_name="${repositories_array[0]}"
            log_info "Found one repository: ${repo_name}"
        else
            log_info "Found ${num_repos} repositories:"
            for i in "${!repositories_array[@]}"; do
                echo "  $((i+1)). ${repositories_array[i]}"
            done
            echo ""
            read -rp "Select repository number (1-${num_repos}): " selection

            if [[ ! "${selection}" =~ ^[0-9]+$ ]] || [[ ${selection} -lt 1 ]] || [[ ${selection} -gt ${num_repos} ]]; then
                log_error "Invalid selection. Exiting."
                exit 1
            fi

            repo_name="${repositories_array[$((selection-1))]}"
            log_info "Selected repository: ${repo_name}"
        fi

        local repository_resource="projects/${PROJECT_ID}/locations/${REGION}/connections/${connection_name}/repositories/${repo_name}"

        # Confirmation prompt
        echo ""
        log_info "About to create trigger with the following configuration:"
        echo "  Trigger name: ${trigger_name}"
        echo "  Connection: ${connection_name}"
        echo "  Repository: ${repo_name}"
        echo "  Branch pattern: ^main$"
        echo "  Build config: cloudbuild.yaml"
        echo "  Region: ${REGION}"
        echo ""
        read -rp "Proceed with trigger creation? (y/N): " confirm

        if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
            log_info "Trigger creation cancelled by user"
            exit 0
        fi

        log_info "Creating GitHub trigger for ${repository_resource}"

        # Create trigger with error handling
        if gcloud builds triggers create github \
            --name="${trigger_name}" \
            --repository="${repository_resource}" \
            --branch-pattern="^main$" \
            --build-config="cloudbuild.yaml" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}" 2>&1 | tee -a "${LOG_FILE}"; then
            log_success "Created GitHub trigger: ${trigger_name}"
        else
            local exit_code=$?
            log_error "Failed to create trigger (exit code: ${exit_code})"
            log_error ""
            log_error "Common causes and solutions:"
            log_error "  1. Repository not granted access to Cloud Build:"
            log_error "     - Visit: https://console.cloud.google.com/cloud-build/repositories"
            log_error "     - Ensure the repository is connected and has proper permissions"
            log_error ""
            log_error "  2. Insufficient IAM permissions:"
            log_error "     - Required role: roles/cloudbuild.builds.editor or higher"
            log_error "     - Visit: https://console.cloud.google.com/iam-admin/iam"
            log_error ""
            log_error "  3. Invalid region:"
            log_error "     - Current region: ${REGION}"
            log_error "     - Ensure the connection exists in this region"
            log_error ""
            log_error "  4. Connection or repository resource not found:"
            log_error "     - Visit: https://console.cloud.google.com/cloud-build/connections"
            log_error ""
            log_error "See full error details in: ${LOG_FILE}"
            exit 1
        fi
    else
        # No GitHub connections - error out instead of silently falling back to CSR
        log_error "No GitHub App connections found."
        log_error ""
        log_error "A GitHub App connection is required to create triggers for GitHub-hosted repositories."
        log_error "To fix this issue, choose one of the following options:"
        log_error ""
        log_error "  1. Create a GitHub App connection in the Cloud Build console:"
        log_error "     https://console.cloud.google.com/cloud-build/connections"
        log_error ""
        log_error "  2. Use Cloud Source Repositories instead (after creating a CSR repo):"
        log_error "     gcloud source repos create whatsapp-mcp"
        log_error "     Then set USE_CSR=true and re-run this script"
        log_error ""
        log_error "  3. Skip trigger creation for now and set up manually later:"
        log_error "     ${SCRIPT_NAME} --skip-trigger"
        exit 1
    fi

    # Describe trigger to confirm
    log_info "Trigger configuration:"
    gcloud builds triggers describe "${trigger_name}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" | tee -a "${LOG_FILE}"

    log_success "Cloud Build trigger configured successfully"
}