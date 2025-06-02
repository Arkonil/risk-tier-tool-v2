# install uv package manager
wget -qO- https://astral.sh/uv/install.sh | bash

# install python packages
uv init --python 3.9.19
uv sync --link-mode=copy --python 3.9.19