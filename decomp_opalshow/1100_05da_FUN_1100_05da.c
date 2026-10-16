
void __cdecl16near FUN_1100_05da(void)

{
  code *pcVar1;
  uint uVar2;
  int iVar3;
  uint in_CX;
  undefined2 in_DX;
  undefined2 extraout_DX;
  undefined2 in_BX;
  undefined2 unaff_SS;
  
  if ((in_CX != 0) && (*(char *)0x1039 == '\0')) {
    do {
      uVar2 = (int)(char)in_DX + in_CX;
      iVar3 = uVar2 - *(uint *)0x1037;
      if (uVar2 < *(uint *)0x1037 || iVar3 == 0) {
        FUN_1100_3444();
        return;
      }
      uVar2 = iVar3 - 1;
      if (uVar2 < in_CX) {
        FUN_1100_3444(uVar2,in_BX);
      }
      if (*(char *)0x103a == '\0') {
        *(undefined1 *)0x1039 = 1;
        pcVar1 = (code *)swi(0x10);
        (*pcVar1)();
        return;
      }
      in_CX = uVar2;
      FUN_1100_0627();
      in_DX = extraout_DX;
    } while (in_CX != 0);
  }
  return;
}

