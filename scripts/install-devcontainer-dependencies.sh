# install uv package manager
wget -qO- https://astral.sh/uv/install.sh | bash

# install python packages
uv init
uv sync --link-mode=copy