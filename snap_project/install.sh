main() {
    date

    cd ..
    root_path=$(pwd)
    project_path=snap_project
    output_path="$project_path/output"
    pack_path="$output_path/pack"

    snapcraft clean && snapcraft pack --output "$pack_path" || return 1

    cd "$pack_path"
    raw_name=$(echo *.snap)
    cd "$root_path"
    full_name="${raw_name%.snap}_$(git describe --tags)_$(date +%s).snap"
    source_path="$pack_path/$raw_name"
    destination_path="$output_path/$full_name"

    mv "$source_path" "$destination_path"

    # Too brutal : data loss.
    # snap remove backroll
    snap install --devmode "$destination_path" && snap logs -n=32 backroll || return 1
    
    date
}

main
