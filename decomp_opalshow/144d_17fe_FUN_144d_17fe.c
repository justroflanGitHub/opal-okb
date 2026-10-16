
undefined2 __cdecl16far FUN_144d_17fe(void)

{
  int iVar1;
  undefined2 *puVar2;
  undefined2 uVar3;
  undefined2 unaff_DS;
  bool bVar4;
  
  bVar4 = *(int *)0x5a4 == 0;
  if (bVar4) {
    iVar1 = FUN_144d_1986();
    if (bVar4) {
      return 0;
    }
    puVar2 = (undefined2 *)(iVar1 + 1U & 0xfffe);
    *(undefined2 *)0x5a4 = puVar2;
    *(undefined2 *)0x5a6 = puVar2;
    *puVar2 = 1;
    puVar2[1] = 0xfffe;
    *(undefined2 *)0x5aa = puVar2 + 2;
  }
  uVar3 = FUN_144d_1847();
  return uVar3;
}

