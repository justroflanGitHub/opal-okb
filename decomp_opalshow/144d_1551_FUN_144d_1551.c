
/* WARNING: Unable to track spacebase fully for stack */

undefined2 __cdecl16near FUN_144d_1551(void)

{
  code *pcVar1;
  undefined2 in_AX;
  int iVar2;
  undefined2 uVar3;
  uint in_DX;
  int unaff_BP;
  uint unaff_DI;
  undefined2 unaff_SS;
  bool bVar4;
  
  bVar4 = unaff_DI < in_DX;
  if (unaff_DI != in_DX) {
    pcVar1 = (code *)swi(0x21);
    iVar2 = (*pcVar1)();
    if ((bVar4) || (*(int *)(unaff_BP + -2) = *(int *)(unaff_BP + -2) + iVar2, iVar2 == 0)) {
      uVar3 = FUN_144d_0ac1();
      return uVar3;
    }
  }
  return in_AX;
}

