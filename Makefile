GENERATED_DIR := generated

.PHONY: generate build clean

# Generate the package source tree from the DTD + transforms config.
generate: pubmed.dtd pubmed_transforms.yaml
	uv run xsdformer build pubmed.dtd \
		--transforms pubmed_transforms.yaml \
		--out-dir $(GENERATED_DIR)

# Build a wheel from the generated source tree.
build: generate
	cd $(GENERATED_DIR) && uv build --out-dir ../dist

clean:
	rm -rf $(GENERATED_DIR) dist
