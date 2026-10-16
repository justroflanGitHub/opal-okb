
undefined2 __cdecl16far FUN_1089_06e8(void)

{
  code *pcVar1;
  undefined2 uVar2;
  int unaff_SI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar3;
  
  bVar3 = *(byte *)0x3b5 < 3;
  if (*(byte *)0x3b5 < 4) {
    pcVar1 = (code *)swi(0x25);
    uVar2 = (*pcVar1)();
    if (!bVar3) {
      uVar2 = 0;
    }
    *(undefined2 *)(unaff_SI + -0x10) = uVar2;
  }
  else {
    pcVar1 = (code *)swi(0x25);
    uVar2 = (*pcVar1)();
    if (!bVar3) {
      uVar2 = 0;
    }
    *(undefined2 *)(unaff_SI + -0x10) = uVar2;
  }
  return *(undefined2 *)(unaff_SI + -0x10);
}

