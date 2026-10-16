
void __cdecl16near FUN_1100_0da6(void)

{
  int iVar1;
  int iVar2;
  int in_CX;
  int in_DX;
  undefined2 unaff_DS;
  
  iVar1 = *(int *)0x10c6;
  iVar2 = iVar1;
  if (iVar1 < in_CX) {
    iVar2 = in_CX;
    in_CX = iVar1;
  }
  *(int *)0x1116 = iVar2;
  *(int *)0x1118 = in_CX;
  iVar1 = *(int *)0x10c8;
  iVar2 = iVar1;
  if (iVar1 < in_DX) {
    iVar2 = in_DX;
    in_DX = iVar1;
  }
  *(int *)0x111a = iVar2;
  *(int *)0x111c = in_DX;
  FUN_1100_0dce();
  return;
}

