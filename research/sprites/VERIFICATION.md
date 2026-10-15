# Verification audit

Source ROM SHA-256:

`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

Verification performed on the final extraction logic:

- Battle far-pointer entries checked: **383/383**
- Battle blocks decompressing to exactly 576 bytes: **383/383**
- Battle 48×48 render path: verified for all entries
- Distinct rendered RGBA battle sprites: **326**
- Defined core records represented: **323**
- Overworld sprite definitions checked: **98/98**
- Overworld exported frames checked: **584**
- Overworld graphics blocks tile-aligned: **98/98**
- OAM frame pointers resolve inside ROM bank 127: **all**
- Every valid OAM tile reference fits its decompressed graphics block: **all**
- Every valid overworld OAM frame uses the expected base OBJ palette slot: **all**
- Reproduction script test: battle core ID 010 (Slime) and overworld sprite 000 frame 0 matched the packaged RGBA pixels exactly
- Validation issues found: **0**

The archive intentionally does not contain the source `.gbc` ROM.
