"""Far Cry 6 / New Dawn module.

Parser: import_xbg_fc6.py — reads FC6 XBG files (version 0x00130049).
Format: HSEM chunk-based, same lineage as FC5 but with extra header field
and evolved chunk content.  Chunk order:
  LTMR → LEKS → EDON → MB2O → KSRP → DIKS → DNKS → ITOM → SDOL
  → DHRM → ZNRM → XOBB → HPSB → FIKS → SDPD → [PMCP] → [PMCU]

Operators: operators_fc6.py — import operator.
"""

from . import operators_fc6
