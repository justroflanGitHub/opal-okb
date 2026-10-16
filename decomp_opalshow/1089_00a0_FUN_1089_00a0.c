
void __cdecl16far FUN_1089_00a0(int param_1,uint param_2)

{
  code *pcVar1;
  int iVar2;
  int extraout_DX;
  int extraout_DX_00;
  undefined1 uVar3;
  
  iVar2 = FUN_1100_0169();
  if (param_1 == 0) {
    FUN_1100_010e(1 - iVar2);
    FUN_1100_0384(0);
  }
  else {
    FUN_1100_0138(1 - iVar2);
    uVar3 = 1;
    pcVar1 = (code *)swi(0x1a);
    (*pcVar1)();
    iVar2 = extraout_DX;
    do {
      pcVar1 = (code *)swi(0x16);
      (*pcVar1)();
      if (!(bool)uVar3) {
        FUN_1089_0106();
      }
      pcVar1 = (code *)swi(0x1a);
      (*pcVar1)();
      uVar3 = extraout_DX_00 - iVar2 == param_2;
    } while ((uint)(extraout_DX_00 - iVar2) < param_2);
  }
  return;
}

