
uint __cdecl16near FUN_1100_0df4(void)

{
  uint in_AX;
  uint uVar1;
  int in_CX;
  int in_DX;
  undefined2 unaff_DS;
  
  uVar1 = in_AX & 0xff00;
  if (in_CX < *(int *)0x10fa) {
    uVar1 = uVar1 + 1;
  }
  if (*(int *)0x10fc < in_CX) {
    uVar1 = uVar1 | 2;
  }
  if (in_DX < *(int *)0x10fe) {
    uVar1 = uVar1 | 4;
  }
  if (*(int *)0x1100 < in_DX) {
    uVar1 = uVar1 | 8;
  }
  return uVar1;
}

