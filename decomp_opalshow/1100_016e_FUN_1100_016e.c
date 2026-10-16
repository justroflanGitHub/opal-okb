
undefined2 * __cdecl16far FUN_1100_016e(undefined2 *param_1)

{
  undefined1 uVar1;
  int iVar2;
  undefined2 uVar3;
  undefined2 *puVar4;
  undefined2 uVar5;
  undefined2 unaff_DS;
  bool bVar6;
  undefined4 uVar7;
  
  uVar5 = (undefined2)((ulong)param_1 >> 0x10);
  puVar4 = (undefined2 *)param_1;
  bVar6 = true;
  uVar3 = 0;
  iVar2 = 0x20;
  uVar7 = FUN_1100_0f84();
  if (!bVar6) {
    uVar7 = CONCAT22((uint)*(byte *)0x2fd * (uint)*(byte *)0x2fe,*(undefined2 *)0x2db);
    uVar3 = *(undefined2 *)0x2dd;
    iVar2 = CONCAT11((char)((uint)iVar2 >> 8),*(undefined1 *)0x2e1) + 1;
  }
  *param_1 = (int)uVar7;
  puVar4[1] = uVar3;
  puVar4[2] = (uint)*(byte *)0x2d9;
  puVar4[3] = (uint)*(byte *)0x2da;
  puVar4[4] = iVar2;
  puVar4[5] = (int)((ulong)uVar7 >> 0x10);
  iVar2 = CONCAT11((char)((ulong)uVar7 >> 0x18),*(undefined1 *)0x2e6) + 1;
  puVar4[6] = iVar2;
  uVar1 = (undefined1)((uint)iVar2 >> 8);
  puVar4[7] = CONCAT11(uVar1,*(undefined1 *)0x2d7);
  puVar4[8] = CONCAT11(uVar1,*(undefined1 *)0x1112);
  puVar4[9] = CONCAT11(uVar1,*(undefined1 *)0x1113);
  puVar4[10] = *(undefined2 *)0x1114;
  return puVar4;
}

