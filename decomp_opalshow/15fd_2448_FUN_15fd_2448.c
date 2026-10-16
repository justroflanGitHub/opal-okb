
void __cdecl16near FUN_15fd_2448(undefined2 param_1,undefined2 param_2)

{
  undefined2 uVar1;
  int iVar2;
  int unaff_SI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  undefined1 in_CF;
  bool bVar3;
  undefined1 in_ZF;
  
  FUN_15fd_0f90();
  FUN_15fd_0f90();
  iVar2 = *(int *)0x6e;
  *(undefined2 *)0x6e = 0;
  FUN_15fd_2261();
  if ((bool)in_CF || (bool)in_ZF) {
    *(int *)0x6e = *(int *)0x6e + -1;
    iVar2 = iVar2 + 1;
  }
  FUN_15fd_2248(iVar2);
  *(undefined2 *)0x96 = 0x66;
  FUN_15fd_0ef1();
  FUN_15fd_24e8();
  if (unaff_SI != 0) {
    uVar1 = 0;
    if (unaff_SI < 0) {
      uVar1 = 0x80;
      unaff_SI = -unaff_SI;
    }
    iVar2 = 0x10;
    do {
      iVar2 = iVar2 + -1;
      bVar3 = unaff_SI < 0;
      unaff_SI = unaff_SI << 1;
    } while (!bVar3);
    *(undefined2 *)0x66 = 0;
    *(undefined2 *)0x68 = 0;
    *(undefined2 *)0x6a = 0;
    *(undefined2 *)0x6c = (int)(CONCAT12(bVar3,unaff_SI) >> 1);
    *(int *)0x6e = iVar2;
    *(undefined2 *)0x70 = uVar1;
    *(undefined2 *)0x96 = 0x5a;
    FUN_15fd_0ef6();
    *(undefined2 *)0x96 = param_2;
    FUN_15fd_0f0d();
  }
  return;
}

