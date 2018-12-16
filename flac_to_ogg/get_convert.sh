#!/bin/bash

set -eux

printf '#!/bin/bash\n\nset -eux\n\n' > convert.sh
$(dirname $(readlink -f $0))/print_conversions.py | sort >> convert.sh
chmod +x convert.sh
