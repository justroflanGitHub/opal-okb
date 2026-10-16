
undefined2 __cdecl16near FUN_1100_0293(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uVar3;
  undefined2 unaff_DS;
  undefined1 in_ZF;
  
  FUN_1100_0f84();
  if (!(bool)in_ZF) {
    FUN_1100_0a73();
    *(undefined2 *)0xffe = *(undefined2 *)0x10be;
    *(undefined2 *)0x1000 = *(undefined2 *)0x10c0;
    *(undefined2 *)0x1008 = 0xffff;
    if (*(char *)0x2d6 != '\x04') {
      FUN_1100_0951();
    }
  }
  *(undefined2 *)0x1002 = 0;
  *(undefined2 *)0x1004 = 0;
  FUN_1100_08f3();
  *(undefined2 *)0x1033 = 0;
  *(undefined2 *)0x1031 = 0;
  *(undefined1 *)0x1039 = 0;
  *(undefined1 *)0x103b = 0;
  *(undefined1 *)0x1012 = 0;
  *(undefined1 *)0x103a = 1;
  bVar1 = *(byte *)0x2d9;
  *(int *)0x1037 = bVar1 - 1;
  bVar2 = *(byte *)0x2da;
  uVar3 = (undefined1)(bVar1 - 1 >> 8);
  *(int *)0x1035 = CONCAT11(uVar3,bVar2) + -1;
  return CONCAT11(uVar3,bVar2 & *(byte *)0x2b9);
}

