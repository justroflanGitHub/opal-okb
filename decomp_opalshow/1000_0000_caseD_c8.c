
void __cdecl16far switchD_1000:6efd::caseD_c8(void)

{
  int *piVar1;
  uint uVar2;
  char cVar3;
  int iVar4;
  uint uVar5;
  undefined2 uVar6;
  int iVar7;
  undefined2 unaff_DS;
  
  FUN_1100_016e(0xa10);
  *(undefined2 *)0xff4 = 0x19;
  iVar4 = *(int *)0xa20;
  if ((iVar4 < 0) || (iVar4 != 2)) {
    if (((iVar4 < 0) || (iVar4 != 4)) &&
       (((iVar4 < 0 || (iVar4 != 8)) && ((iVar4 < 0 || (iVar4 != 0x10)))))) {
      *(undefined2 *)0xfee = 0x280;
      *(undefined2 *)0xff2 = 0x15e;
      FUN_144d_0227();
    }
    else {
      *(undefined2 *)0xfee = 0x280;
      *(undefined2 *)0xff2 = 0x15e;
      if (*(int *)0xa22 < 3) {
        *(undefined2 *)0xff2 = 200;
      }
      FUN_144d_0227();
    }
  }
  else {
    *(undefined2 *)0xfee = 0x280;
    *(undefined2 *)0xff2 = 200;
    FUN_144d_0227();
  }
  FUN_144d_027b();
  FUN_144d_0227();
  FUN_144d_018b();
  FUN_144d_0257();
  *(int *)0xff8 = *(int *)0xfee / 0x50;
  *(int *)0xffa = *(int *)0xff2 / *(int *)0xff4;
  *(int *)0xd6e = *(int *)0xff8 / 2 + 1;
  *(int *)0xd70 = *(int *)0xffa / 2 + 1;
  *(undefined2 *)0xe38 = 5;
  *(undefined2 *)0xe3a = 6;
  *(undefined2 *)0xe34 = 1;
  *(undefined2 *)0xe36 = 3;
  *(undefined2 *)0xe32 = 0x19;
  *(undefined2 *)0xfec = 1;
  while (*(int *)0xfec < 7) {
    if (*(int *)0xa20 == 2) {
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x6b);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xde6) = iVar4;
      *(int *)(iVar7 + 0xde8) = iVar4 >> 0xf;
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x6b);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xdfe) = iVar4;
      *(int *)(iVar7 + 0xe00) = iVar4 >> 0xf;
      iVar4 = *(int *)0xfec;
      cVar3 = *(char *)(iVar4 + 0x6b);
    }
    else {
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x53);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xde6) = iVar4;
      *(int *)(iVar7 + 0xde8) = iVar4 >> 0xf;
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x53);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xdfe) = iVar4;
      *(int *)(iVar7 + 0xe00) = iVar4 >> 0xf;
      iVar4 = *(int *)0xfec;
      cVar3 = *(char *)(iVar4 + 0x53);
    }
    *(int *)(iVar4 * 4 + 0xe16) = (int)cVar3;
    *(int *)(iVar4 * 4 + 0xe18) = (int)cVar3 >> 0xf;
    *(int *)0xfec = *(int *)0xfec + 1;
  }
  *(undefined2 *)0xfec = 0;
  while (*(int *)0xfec < 7) {
    *(undefined2 *)(*(int *)0xfec * 0x52 + 0xa32) = 1;
    *(undefined2 *)(*(int *)0xfec * 0x52 + 0xa36) = 0x50;
    *(undefined2 *)(*(int *)0xfec * 0x52 + 0xa30) = 2;
    *(int *)(*(int *)0xfec * 0x52 + 0xa34) = *(int *)0xff4 + -2;
    uVar2 = *(uint *)0xff4;
    iVar4 = *(int *)0xfec;
    *(int *)(iVar4 * 0x52 + 0xa38) = uVar2 - 5;
    *(int *)(iVar4 * 0x52 + 0xa3a) = ((int)uVar2 >> 0xf) - (uint)(uVar2 < 5);
    iVar4 = *(int *)0xfec;
    *(undefined2 *)(iVar4 * 0x52 + 0xa3c) = 0x4e;
    *(undefined2 *)(iVar4 * 0x52 + 0xa3e) = 0;
    *(undefined2 *)0xff0 = 1;
    while (*(int *)0xff0 < 7) {
      iVar7 = *(int *)0xff0 * 4;
      iVar4 = *(int *)0xfec;
      uVar6 = *(undefined2 *)(iVar7 + 0xde8);
      *(undefined2 *)(iVar4 * 0x52 + iVar7 + 0xa3c) = *(undefined2 *)(iVar7 + 0xde6);
      *(undefined2 *)(iVar4 * 0x52 + iVar7 + 0xa3e) = uVar6;
      *(int *)0xff0 = *(int *)0xff0 + 1;
    }
    *(int *)0xfec = *(int *)0xfec + 1;
  }
  *(undefined2 *)0xd72 = 1;
  *(int *)0xd9a = *(int *)0xff4 + -1;
  *(undefined2 *)0xdc2 = *(undefined2 *)0xff4;
  *(undefined2 *)0xfec = 1;
  do {
    *(undefined2 *)(*(int *)0xfec * 0x28 + 0xd4c) = 0xb;
    *(undefined2 *)(*(int *)0xfec * 0x28 + 0xd50) = 0x33;
    *(undefined2 *)(*(int *)0xfec * 0x28 + 0xd4e) = *(undefined2 *)(*(int *)0xfec * 0x28 + 0xd4a);
    iVar4 = *(int *)0xfec;
    *(undefined2 *)(iVar4 * 0x28 + 0xd52) = 1;
    *(undefined2 *)(iVar4 * 0x28 + 0xd54) = 0;
    iVar4 = *(int *)0xfec;
    *(undefined2 *)(iVar4 * 0x28 + 0xd56) = 0x28;
    *(undefined2 *)(iVar4 * 0x28 + 0xd58) = 0;
    *(int *)0xfec = *(int *)0xfec + 1;
  } while (*(int *)0xfec < 4);
  *(undefined2 *)0xfec = 1;
  while (*(int *)0xfec < 7) {
    if (*(int *)0xa20 == 2) {
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x59);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xd7e) = iVar4;
      *(int *)(iVar7 + 0xd80) = iVar4 >> 0xf;
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x5f);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xda6) = iVar4;
      *(int *)(iVar7 + 0xda8) = iVar4 >> 0xf;
      iVar4 = *(int *)0xfec;
      cVar3 = *(char *)(iVar4 + 0x65);
    }
    else {
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x41);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xd7e) = iVar4;
      *(int *)(iVar7 + 0xd80) = iVar4 >> 0xf;
      iVar4 = (int)*(char *)(*(int *)0xfec + 0x47);
      iVar7 = *(int *)0xfec * 4;
      *(int *)(iVar7 + 0xda6) = iVar4;
      *(int *)(iVar7 + 0xda8) = iVar4 >> 0xf;
      iVar4 = *(int *)0xfec;
      cVar3 = *(char *)(iVar4 + 0x4d);
    }
    *(int *)(iVar4 * 4 + 0xdce) = (int)cVar3;
    *(int *)(iVar4 * 4 + 0xdd0) = (int)cVar3 >> 0xf;
    *(int *)0xfec = *(int *)0xfec + 1;
  }
  uVar2 = *(uint *)0xa34;
  iVar4 = FUN_144d_002a(uVar2 + 1,((int)uVar2 >> 0xf) + (uint)(0xfffe < uVar2),2,0);
  uVar5 = iVar4 + 1;
  *(uint *)0xa82 = uVar5;
  uVar2 = *(uint *)0xa86;
  *(int *)0xa8a = (uVar2 - uVar5) + -1;
  *(int *)0xa8c =
       ((((int)uVar2 >> 0xf) - ((int)uVar5 >> 0xf)) - (uint)(uVar2 < uVar5)) -
       (uint)(uVar2 - uVar5 == 0);
  *(uint *)0xad8 = uVar5;
  uVar2 = *(uint *)0xad4;
  uVar5 = *(uint *)0xad8;
  *(int *)0xadc = (uVar5 - uVar2) + -1;
  *(int *)0xade =
       ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
       (uint)(uVar5 - uVar2 == 0);
  *(undefined2 *)0xbce = *(undefined2 *)0xa82;
  *(undefined2 *)0xbd0 = 0x28;
  uVar2 = *(uint *)0xbca;
  uVar5 = *(uint *)0xbce;
  *(int *)0xbd2 = (uVar5 - uVar2) + -1;
  *(int *)0xbd4 =
       ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
       (uint)(uVar5 - uVar2 == 0);
  *(undefined2 *)0xbd6 = 0x26;
  *(undefined2 *)0xbd8 = 0;
  *(undefined2 *)0xc20 = *(undefined2 *)0xbce;
  *(undefined2 *)0xc1e = 0x28;
  uVar2 = *(uint *)0xc1c;
  uVar5 = *(uint *)0xc20;
  *(int *)0xc24 = (uVar5 - uVar2) + -1;
  *(int *)0xc26 =
       ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
       (uint)(uVar5 - uVar2 == 0);
  *(undefined2 *)0xc28 = 0x27;
  *(undefined2 *)0xc2a = 0;
  uVar2 = *(uint *)0xbce;
  *(uint *)0xb26 = uVar2;
  *(undefined2 *)0xb2c = 0x28;
  uVar5 = *(uint *)0xb2a;
  *(int *)0xb2e = (uVar5 - uVar2) + -1;
  *(int *)0xb30 =
       ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
       (uint)(uVar5 - uVar2 == 0);
  *(undefined2 *)0xb32 = 0x26;
  *(undefined2 *)0xb34 = 0;
  *(uint *)0xb78 = uVar2;
  *(undefined2 *)0xb7a = 0x28;
  uVar5 = *(uint *)0xb7c;
  *(int *)0xb80 = (uVar5 - uVar2) + -1;
  *(int *)0xb82 =
       ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
       (uint)(uVar5 - uVar2 == 0);
  *(undefined2 *)0xb84 = 0x27;
  *(undefined2 *)0xb86 = 0;
  *(undefined2 *)0xfec = 0;
  do {
    *(int *)(*(int *)0xfec * 0x52 + 0xa58) = *(int *)0xff8 + 1;
    *(int *)(*(int *)0xfec * 0x52 + 0xa5c) = *(int *)0xfee - *(int *)0xff8;
    *(int *)(*(int *)0xfec * 0x52 + 0xa5a) = *(int *)0xffa * 2 + 1;
    *(int *)(*(int *)0xfec * 0x52 + 0xa5e) = (*(int *)0xff4 + -2) * *(int *)0xffa;
    *(int *)0xfec = *(int *)0xfec + 1;
  } while (*(int *)0xfec < 7);
  *(int *)0xbf8 = (*(int *)0xbce + -1) * *(int *)0xffa;
  *(int *)0xbf6 = *(int *)0xff8 * 0x27;
  *(undefined2 *)0xc4a = *(undefined2 *)0xbf8;
  *(int *)0xc44 = *(int *)0xbf6 + *(int *)0xa58;
  *(int *)0xaac = *(int *)0xbf8 + *(int *)0xffa + 1;
  *(undefined2 *)0xb02 = *(undefined2 *)0xbf8;
  *(undefined2 *)0xba0 = *(undefined2 *)0xc44;
  *(undefined2 *)0xba2 = *(undefined2 *)0xaac;
  *(undefined2 *)0xb52 = *(undefined2 *)0xbf6;
  *(undefined2 *)0xb50 = *(undefined2 *)0xaac;
  *(undefined2 *)0xfec = 0;
  do {
    *(undefined2 *)0xff6 = *(undefined2 *)0xd70;
    if ((((*(int *)0xfec == 0) || (*(int *)0xfec == 1)) || (*(int *)0xfec == 3)) ||
       (*(int *)0xfec == 4)) {
      *(undefined2 *)0xff6 = 0xffff;
    }
    iVar4 = *(int *)0xfec * 0x52;
    uVar2 = *(uint *)(iVar4 + 0xa58);
    uVar5 = *(uint *)(iVar4 + 0xa5c);
    *(int *)(iVar4 + 0xa62) = uVar5 - uVar2;
    *(int *)(iVar4 + 0xa64) = (((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2);
    iVar4 = *(int *)0xfec * 0x52;
    uVar2 = *(uint *)(iVar4 + 0xa5a);
    uVar5 = *(uint *)(iVar4 + 0xa5e);
    *(int *)(iVar4 + 0xa66) = (uVar5 - uVar2) + -1;
    *(int *)(iVar4 + 0xa68) =
         ((((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2)) -
         (uint)(uVar5 - uVar2 == 0);
    iVar4 = *(int *)0xfec;
    FUN_144d_0233();
    FUN_144d_027b();
    FUN_144d_0227();
    caseD_c();
    uVar6 = FUN_144d_02b8();
    *(undefined2 *)(iVar4 * 0x52 + 0xa60) = uVar6;
    iVar4 = *(int *)0xfec * 0x52;
    uVar2 = *(uint *)(iVar4 + 0xa58);
    uVar5 = *(uint *)(iVar4 + 0xa60);
    *(int *)(iVar4 + 0xa6a) = uVar5 - uVar2;
    *(int *)(iVar4 + 0xa6c) = (((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2);
    piVar1 = (int *)(*(int *)0xfec * 0x52 + 0xa58);
    *piVar1 = *piVar1 - *(int *)0xd6e;
    piVar1 = (int *)(*(int *)0xfec * 0x52 + 0xa5c);
    *piVar1 = *piVar1 + *(int *)0xd6e;
    piVar1 = (int *)(*(int *)0xfec * 0x52 + 0xa5a);
    *piVar1 = *piVar1 - *(int *)0xd70;
    piVar1 = (int *)(*(int *)0xfec * 0x52 + 0xa5e);
    *piVar1 = *piVar1 + *(int *)0xff6;
    *(int *)0xfec = *(int *)0xfec + 1;
  } while (*(int *)0xfec < 7);
  uVar6 = FUN_144d_002a(*(undefined2 *)0xa62,*(undefined2 *)0xa64,3,0);
  *(undefined2 *)0xff8 = uVar6;
  uVar6 = FUN_144d_002a(*(undefined2 *)0xa66,*(undefined2 *)0xa68,2,0);
  *(undefined2 *)0xffa = uVar6;
  iVar7 = *(int *)0xa58 + *(int *)0xd6e;
  *(int *)0xc6e = iVar7;
  *(int *)0xcec = iVar7;
  iVar4 = *(int *)0xff8;
  *(int *)0xc72 = iVar7 + iVar4;
  *(int *)0xcf0 = iVar7 + iVar4;
  FUN_144d_0227();
  FUN_144d_027b();
  FUN_144d_0227();
  caseD_c();
  uVar6 = FUN_144d_02b8();
  *(undefined2 *)0xc76 = uVar6;
  *(undefined2 *)0xcf4 = uVar6;
  iVar7 = *(int *)0xc72 + 1;
  *(int *)0xc98 = iVar7;
  *(int *)0xd16 = iVar7;
  iVar4 = *(int *)0xff8;
  *(int *)0xc9c = iVar7 + iVar4;
  *(int *)0xd1a = iVar7 + iVar4;
  FUN_144d_0227();
  FUN_144d_027b();
  FUN_144d_0227();
  caseD_c();
  uVar6 = FUN_144d_02b8();
  *(undefined2 *)0xca0 = uVar6;
  *(undefined2 *)0xd1e = uVar6;
  iVar4 = *(int *)0xc9c;
  *(int *)0xcc2 = iVar4 + 1;
  *(int *)0xd40 = iVar4 + 1;
  iVar4 = *(int *)0xa5c;
  iVar7 = *(int *)0xd6e;
  *(int *)0xcc6 = iVar4 - iVar7;
  *(int *)0xd44 = iVar4 - iVar7;
  FUN_144d_0227();
  FUN_144d_027b();
  FUN_144d_0227();
  caseD_c();
  uVar6 = FUN_144d_02b8();
  *(undefined2 *)0xcca = uVar6;
  *(undefined2 *)0xd48 = uVar6;
  iVar4 = *(int *)0xa5a;
  iVar7 = *(int *)0xd70;
  *(int *)0xc70 = iVar4 + iVar7;
  iVar4 = iVar4 + iVar7 + *(int *)0xffa;
  *(int *)0xc74 = iVar4;
  *(int *)0xcee = iVar4 + 1;
  *(int *)0xcf2 = *(int *)0xa5e - *(int *)0xd70;
  *(undefined2 *)0xc9a = *(undefined2 *)0xc70;
  *(undefined2 *)0xc9e = *(undefined2 *)0xc74;
  *(undefined2 *)0xd18 = *(undefined2 *)0xcee;
  *(undefined2 *)0xd1c = *(undefined2 *)0xcf2;
  *(undefined2 *)0xcc4 = *(undefined2 *)0xc70;
  *(undefined2 *)0xcc8 = *(undefined2 *)0xc74;
  *(undefined2 *)0xd42 = *(undefined2 *)0xcee;
  *(undefined2 *)0xd46 = *(undefined2 *)0xcf2;
  *(undefined2 *)0xfec = 1;
  do {
    piVar1 = (int *)(*(int *)0xfec * 0x2a + 0xc46);
    *piVar1 = *piVar1 + 10;
    iVar4 = *(int *)0xfec * 0x2a;
    uVar2 = *(uint *)(iVar4 + 0xc46);
    uVar5 = *(uint *)(iVar4 + 0xc4a);
    *(int *)(iVar4 + 0xc52) = uVar5 - uVar2;
    *(int *)(iVar4 + 0xc54) = (((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2);
    iVar4 = *(int *)0xfec;
    FUN_144d_0233();
    FUN_144d_027b();
    FUN_144d_0227();
    caseD_c();
    uVar6 = FUN_144d_02b8();
    *(undefined2 *)(iVar4 * 0x2a + 0xc48) = uVar6;
    iVar4 = *(int *)0xfec * 0x2a;
    uVar2 = *(uint *)(iVar4 + 0xc44);
    uVar5 = *(uint *)(iVar4 + 0xc48);
    *(int *)(iVar4 + 0xc4e) = uVar5 - uVar2;
    *(int *)(iVar4 + 0xc50) = (((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2);
    piVar1 = (int *)(*(int *)0xfec * 0x2a + 0xcc4);
    *piVar1 = *piVar1 + 10;
    iVar4 = *(int *)0xfec * 0x2a;
    uVar2 = *(uint *)(iVar4 + 0xcc4);
    uVar5 = *(uint *)(iVar4 + 0xcc8);
    *(int *)(iVar4 + 0xcd0) = uVar5 - uVar2;
    *(int *)(iVar4 + 0xcd2) = (((int)uVar5 >> 0xf) - ((int)uVar2 >> 0xf)) - (uint)(uVar5 < uVar2);
    *(undefined2 *)(*(int *)0xfec * 0x2a + 0xcc6) = *(undefined2 *)(*(int *)0xfec * 0x2a + 0xc48);
    iVar4 = *(int *)0xfec * 0x2a;
    uVar6 = *(undefined2 *)(iVar4 + 0xc50);
    *(undefined2 *)(iVar4 + 0xccc) = *(undefined2 *)(iVar4 + 0xc4e);
    *(undefined2 *)(iVar4 + 0xcce) = uVar6;
    *(int *)0xfec = *(int *)0xfec + 1;
  } while (*(int *)0xfec < 4);
  return;
}

