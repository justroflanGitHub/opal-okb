
undefined2 __cdecl16near FUN_1100_0a2c(void)

{
  undefined2 in_AX;
  int iVar1;
  int iVar2;
  undefined2 unaff_DS;
  
  iVar2 = 0;
  iVar1 = *(int *)0x10f6;
  if (*(char *)0x10f5 == '\0') {
    iVar2 = *(int *)0x10fa;
    iVar1 = *(int *)0x10fc;
  }
  *(int *)0x1106 = iVar1 - iVar2;
  *(int *)0x10be = iVar2 + ((iVar1 - iVar2) + 1U >> 1);
  iVar2 = 0;
  iVar1 = *(int *)0x10f8;
  if (*(char *)0x10f5 == '\0') {
    iVar2 = *(int *)0x10fe;
    iVar1 = *(int *)0x1100;
  }
  *(int *)0x1108 = iVar1 - iVar2;
  *(int *)0x10c0 = iVar2 + ((iVar1 - iVar2) + 1U >> 1);
  return in_AX;
}

